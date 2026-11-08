$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
$vite = Join-Path $root 'frontend\node_modules\vite\bin\vite.js'
$nodeCommand = Get-Command node -ErrorAction SilentlyContinue

if (-not (Test-Path -LiteralPath $python)) {
    throw 'Python environment not found. Run: py -m venv .venv; .\.venv\Scripts\python -m pip install -r backend\requirements.txt'
}
if (-not (Test-Path -LiteralPath $vite) -or -not $nodeCommand) {
    throw 'Frontend dependencies not found. Run pnpm install in the frontend folder first.'
}
if (-not (Test-Path -LiteralPath (Join-Path $root 'data\catalog.csv')) -or -not (Test-Path -LiteralPath (Join-Path $root 'data\visual_descriptions.csv'))) {
    throw 'Private CSV files are missing. Put catalog.csv and visual_descriptions.csv in data\ first.'
}

$local = Join-Path $root '.local'
New-Item -ItemType Directory -Force -Path $local | Out-Null
$db = Join-Path $root 'data\wardrobe.db'
$itemCount = 0
if (Test-Path -LiteralPath $db) {
    $countOutput = & $python -c "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); print(c.execute('select count(*) from wardrobe_items').fetchone()[0]); c.close()" $db 2>$null
    if ($LASTEXITCODE -eq 0) { [int]::TryParse(($countOutput | Select-Object -Last 1), [ref]$itemCount) | Out-Null }
}
if ($itemCount -eq 0) {
    & $python (Join-Path $root 'backend\scripts\import_catalog.py')
    if ($LASTEXITCODE -ne 0) { throw 'Initial catalog import failed.' }
}

$backendLog = Join-Path $local 'backend.log'
$frontendLog = Join-Path $local 'frontend.log'
$backendErrorLog = Join-Path $local 'backend-error.log'
$frontendErrorLog = Join-Path $local 'frontend-error.log'
$backendPath = Join-Path $root 'backend'
$backendArguments = @('-m','uvicorn','app.main:app','--app-dir',("`"$backendPath`""),'--host','127.0.0.1','--port','8000')
$frontendArguments = @( "`"$vite`"", '--host','127.0.0.1','--port','5173')
$backendProcess = Start-Process -FilePath $python -ArgumentList $backendArguments -WorkingDirectory $root -WindowStyle Hidden -PassThru -RedirectStandardOutput $backendLog -RedirectStandardError $backendErrorLog
$frontendProcess = Start-Process -FilePath $nodeCommand.Source -ArgumentList $frontendArguments -WorkingDirectory (Join-Path $root 'frontend') -WindowStyle Hidden -PassThru -RedirectStandardOutput $frontendLog -RedirectStandardError $frontendErrorLog
@{ backend_pid = $backendProcess.Id; frontend_pid = $frontendProcess.Id } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $local 'servers.json') -Encoding utf8
Start-Sleep -Seconds 2
Start-Process 'http://127.0.0.1:5173'
Write-Output 'My Wardrobe is starting at http://127.0.0.1:5173'
Write-Output 'API docs: http://127.0.0.1:8000/docs'
Write-Output 'To stop both services, run .\stop.ps1'
