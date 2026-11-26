param([int]$Port=8000)
$ErrorActionPreference='Stop'
$scholarRoot=Split-Path -Parent $PSScriptRoot
$scholarPython=Join-Path $scholarRoot '.venv\Scripts\python.exe'
$scholarStatePath=Join-Path $scholarRoot '.runtime\public-preview.json'
$scholarExe=Join-Path $scholarRoot '.runtime\cloudflared\cloudflared-windows-amd64.exe'
$scholarLogs=Join-Path $scholarRoot '.runtime\logs'
$scholarHealth=Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/health" -TimeoutSec 5
if($scholarHealth.application -ne 'scholarship-map'){throw 'Start the ScholarshipMap application first.'}
Push-Location $scholarRoot
try {
    & $scholarPython scripts/fetch-cloudflared.py
    if($LASTEXITCODE -ne 0){throw 'Could not verify the official cloudflared binary.'}
    $scholarState=$null
    if(Test-Path -LiteralPath $scholarStatePath){$scholarState=Get-Content -LiteralPath $scholarStatePath -Raw|ConvertFrom-Json}
    if($scholarState -and ($scholarState.provider -in @('localhost.run','pinggy') -or $scholarState.port -ne $Port)){
        & (Join-Path $PSScriptRoot 'Stop-PublicPreview.ps1')
        $scholarState=$null
    }
    $scholarExisting=if($scholarState){Get-Process -Id $scholarState.pid -ErrorAction SilentlyContinue}else{$null}
    if($scholarExisting -and $scholarExisting.Path -eq $scholarExe -and $scholarState.port -eq $Port){
        if($scholarState.url){Write-Output $scholarState.url;return}
    } else {
        New-Item -ItemType Directory -Force -Path $scholarLogs|Out-Null
        $scholarArguments=@('tunnel','--url',"http://127.0.0.1:$Port",'--no-autoupdate','--protocol','http2','--edge-ip-version','4')
        $scholarProcess=Start-Process -FilePath $scholarExe -ArgumentList $scholarArguments -WorkingDirectory $scholarRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $scholarLogs 'public-preview.out.log') -RedirectStandardError (Join-Path $scholarLogs 'public-preview.err.log')
        $scholarState=@{pid=$scholarProcess.Id;provider='cloudflare';port=$Port;started_at=[DateTimeOffset]::UtcNow.ToString('o');url=$null}
        $scholarState|ConvertTo-Json|Set-Content -LiteralPath $scholarStatePath -Encoding utf8
    }
    for($scholarAttempt=0;$scholarAttempt -lt 80;$scholarAttempt++){
        $scholarText=Get-Content -LiteralPath (Join-Path $scholarLogs 'public-preview.err.log') -Raw -ErrorAction SilentlyContinue
        if($scholarText -match 'https://(?!api\.|www\.)[a-z0-9-]+\.trycloudflare\.com'){
            $scholarUrl=$Matches[0]
            try {
                $scholarPublicHealth=Invoke-RestMethod -Uri "$scholarUrl/api/health" -TimeoutSec 5
                if($scholarPublicHealth.application -ne 'scholarship-map'){throw 'Public endpoint is not this application.'}
            } catch {Start-Sleep -Milliseconds 500;continue}
            $scholarState=@{pid=$scholarState.pid;port=$Port;started_at=$scholarState.started_at;url=$scholarUrl;mode='temporary_local_https_tunnel'}
            $scholarState|ConvertTo-Json|Set-Content -LiteralPath $scholarStatePath -Encoding utf8
            Write-Output $scholarUrl
            Write-Output 'Temporary HTTPS preview. Keep this computer, the app services and cloudflared running.'
            return
        }
        Start-Sleep -Milliseconds 500
    }
    throw 'No public URL yet. Inspect .runtime/logs/public-preview.err.log; the owned process state was retained.'
} finally {Pop-Location}
