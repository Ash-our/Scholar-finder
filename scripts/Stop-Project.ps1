$ErrorActionPreference = 'Stop'
$scholarRoot = Split-Path -Parent $PSScriptRoot
$scholarPrefix = $scholarRoot.TrimEnd('\') + '\'
if(Test-Path -LiteralPath (Join-Path $scholarRoot '.runtime\public-preview.json')){& (Join-Path $PSScriptRoot 'Stop-PublicPreview.ps1')}
function Stop-ScholarTree([int]$ScholarProcessId) {
    $scholarChildren = Get-CimInstance Win32_Process -Filter "ParentProcessId=$ScholarProcessId" -ErrorAction SilentlyContinue
    foreach ($scholarChild in $scholarChildren) {
        # The root is validated before traversal. Python venv launchers can
        # spawn the base Python outside this directory; it is still our child.
        Stop-ScholarTree $scholarChild.ProcessId
    }
    Stop-Process -Id $ScholarProcessId -ErrorAction SilentlyContinue
}
foreach ($scholarPidFile in @('.runtime\app-processes.json','.runtime\services.json')) {
    $scholarPidPath = Join-Path $scholarRoot $scholarPidFile
    if (-not (Test-Path -LiteralPath $scholarPidPath)) { continue }
    $scholarEntries = Get-Content -LiteralPath $scholarPidPath -Raw | ConvertFrom-Json -AsHashtable
    foreach ($scholarEntry in $scholarEntries.GetEnumerator()) {
        $scholarProcessId = [int]$scholarEntry.Value
        $scholarProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$scholarProcessId" -ErrorAction SilentlyContinue
        if (-not $scholarProcess) { continue }
        # PID reuse must not stop another application. The process must still
        # identify this checkout or this checkout's portable service data.
        if (($scholarProcess.CommandLine -and $scholarProcess.CommandLine.Contains($scholarPrefix, [StringComparison]::OrdinalIgnoreCase)) -or
            ($scholarProcess.ExecutablePath -and $scholarProcess.ExecutablePath.StartsWith($scholarPrefix, [StringComparison]::OrdinalIgnoreCase))) {
            Stop-ScholarTree $scholarProcessId
            Write-Output ('Stopped project process: ' + $scholarEntry.Key)
        }
    }
}
Write-Output 'Stored data and checkpoints were retained.'
