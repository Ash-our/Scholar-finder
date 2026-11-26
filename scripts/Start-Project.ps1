param([int]$Port = 8000)
$ErrorActionPreference = 'Stop'
$scholarRoot = Split-Path -Parent $PSScriptRoot
$scholarPrefix = $scholarRoot.TrimEnd('\') + '\'
$scholarRuntime = Join-Path $scholarRoot '.runtime'
$scholarLogs = Join-Path $scholarRuntime 'logs'
New-Item -ItemType Directory -Force -Path $scholarLogs | Out-Null
$scholarPython = Join-Path $scholarRoot '.venv\Scripts\python.exe'
$scholarSparkPython = $scholarPython
if (-not (Test-Path -LiteralPath $scholarPython)) { throw 'Run Setup-Project.ps1 first.' }
Push-Location $scholarRoot
try {
    & (Join-Path $PSScriptRoot 'Start-LocalServices.ps1')
    $scholarReady = $false
    for ($scholarAttempt=0; $scholarAttempt -lt 30; $scholarAttempt++) {
        & $scholarPython -m scholarship_map.cli init *> (Join-Path $scholarLogs 'init.log')
        if ($LASTEXITCODE -eq 0) { $scholarReady=$true; break }
        Start-Sleep -Seconds 2
    }
    if (-not $scholarReady) { throw 'Kafka/Mongo did not become ready; inspect .runtime/logs.' }
    if (-not (Test-Path -LiteralPath 'frontend\dist\index.html')) { throw 'Build the frontend first: cd frontend; npm run build' }
    $scholarOwnedPath = Join-Path $scholarRuntime 'app-processes.json'
    $scholarOwned = @{}
    if (Test-Path -LiteralPath $scholarOwnedPath) { $scholarOwned = Get-Content -LiteralPath $scholarOwnedPath -Raw | ConvertFrom-Json -AsHashtable }
    function Start-ScholarWorker([string]$Name,[string]$Executable,[string]$Arguments,[string]$Pattern) {
        $scholarExisting = Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object {
            $_.ExecutablePath -and $_.ExecutablePath.StartsWith($scholarPrefix, [StringComparison]::OrdinalIgnoreCase) -and $_.CommandLine -match $Pattern
        } | Select-Object -First 1
        if ($scholarExisting) { $scholarOwned[$Name]=$scholarExisting.ProcessId; return }
        $scholarWorker = Start-Process -FilePath $Executable -ArgumentList $Arguments -WorkingDirectory $scholarRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $scholarLogs "$Name.out.log") -RedirectStandardError (Join-Path $scholarLogs "$Name.err.log")
        $scholarOwned[$Name]=$scholarWorker.Id
    }
    Start-ScholarWorker 'streaming' $scholarSparkPython '-X utf8 -m scholarship_map.cli stream' 'scholarship_map\.cli\s+stream|scholarship_map\.streaming.*run_streaming'
    Start-ScholarWorker 'collectors' $scholarPython '-X utf8 -m scholarship_map.cli collect --watch --interval 21600' 'scholarship_map\.cli\s+collect.*--watch'
    Start-ScholarWorker 'batch' $scholarSparkPython '-X utf8 -m scholarship_map.cli batch --watch --interval 900' 'scholarship_map\.cli\s+batch.*--watch'
    try {
        $scholarHealth = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/health" -TimeoutSec 3
        if ($scholarHealth.application -ne 'scholarship-map') { throw 'Port belongs to another application.' }
        $scholarApiExisting = Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object {
            $_.ExecutablePath -and $_.ExecutablePath.StartsWith($scholarPrefix, [StringComparison]::OrdinalIgnoreCase) -and $_.CommandLine -match 'uvicorn scholarship_map.api:app'
        } | Select-Object -First 1
        if ($scholarApiExisting) { $scholarOwned['api']=$scholarApiExisting.ProcessId }
    } catch {
        $scholarListener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        if ($scholarListener) { throw "Port $Port is busy; choose another -Port." }
        Start-ScholarWorker 'api' $scholarPython "-m uvicorn scholarship_map.api:app --host 127.0.0.1 --port $Port" 'uvicorn scholarship_map.api:app'
    }
    $scholarOwned | ConvertTo-Json | Set-Content -LiteralPath $scholarOwnedPath -Encoding utf8
    Write-Output "Scholarship Map: http://127.0.0.1:$Port"
    Write-Output 'The collectors poll every 6 hours; Spark consumes updates continuously; batch analysis runs every 15 minutes.'
} finally { Pop-Location }
