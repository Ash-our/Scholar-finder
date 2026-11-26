$ErrorActionPreference='Stop'
$scholarRoot=Split-Path -Parent $PSScriptRoot
$scholarStatePath=Join-Path $scholarRoot '.runtime\public-preview.json'
if(-not(Test-Path -LiteralPath $scholarStatePath)){return}
$scholarState=Get-Content -LiteralPath $scholarStatePath -Raw|ConvertFrom-Json
$scholarProcess=Get-Process -Id $scholarState.pid -ErrorAction SilentlyContinue
if(-not $scholarProcess){return}
$scholarExpected=Join-Path $scholarRoot '.runtime\cloudflared\cloudflared-windows-amd64.exe'
if($scholarState.provider -in @('localhost.run','pinggy')){
    $scholarExpected=(Get-Command ssh.exe -ErrorAction Stop).Source
    $scholarCommand=(Get-CimInstance Win32_Process -Filter "ProcessId=$($scholarState.pid)" -ErrorAction SilentlyContinue).CommandLine
    if(-not $scholarCommand -or -not $scholarCommand.Contains((Join-Path $scholarRoot '.runtime\preview_ed25519'),[StringComparison]::OrdinalIgnoreCase)){
        throw 'Refused SSH process without the project-specific preview key.'
    }
}
if($scholarProcess -and $scholarProcess.Path -eq $scholarExpected){Stop-Process -Id $scholarProcess.Id;Write-Output 'Stopped the project public preview.'}
