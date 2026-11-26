param([string]$Python = 'python', [switch]$SkipNativeDownloads)
$ErrorActionPreference = 'Stop'
$scholarRoot = Split-Path -Parent $PSScriptRoot
Push-Location $scholarRoot
try {
    if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) { & $Python -m venv .venv }
    if ($LASTEXITCODE -ne 0) { throw 'Python environment creation failed.' }
    & .\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt -r requirements-dev.lock.txt -r requirements-spark.lock.txt
    if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }
    & .\.venv\Scripts\python.exe -m pip install --no-deps -e .
    if ($LASTEXITCODE -ne 0) { throw 'Project installation failed.' }
    Push-Location frontend
    try {
        npm ci --ignore-scripts --no-fund --no-audit
        if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
        npm run build
        if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
    } finally { Pop-Location }
    if (-not $SkipNativeDownloads) {
        & .\.venv\Scripts\python.exe scripts/fetch-native-runtime.py
        if ($LASTEXITCODE -ne 0) { throw 'Native service download failed.' }
        & .\.venv\Scripts\python.exe scripts/fetch-java21.py
        if ($LASTEXITCODE -ne 0) { throw 'Java download failed.' }
        & .\.venv\Scripts\python.exe scripts/fetch-hadoop-windows.py
        if ($LASTEXITCODE -ne 0) { throw 'Windows Hadoop libraries failed.' }
    }
    Write-Output 'Setup complete. Run .\scripts\Start-Project.ps1'
} finally { Pop-Location }
