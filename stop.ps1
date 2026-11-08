$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$statePath = Join-Path $root '.local\servers.json'
if (-not (Test-Path -LiteralPath $statePath)) {
    Write-Output 'No My Wardrobe server state was found.'
    exit 0
}
$state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
$nodeCommand = Get-Command node -ErrorAction SilentlyContinue
$pythonPath = Join-Path $root '.venv\Scripts\python.exe'
$expected = @(
    @{ Id = [int]$state.backend_pid; Path = $pythonPath; Marker = 'uvicorn app.main:app' },
    @{ Id = [int]$state.frontend_pid; Path = if ($nodeCommand) { $nodeCommand.Source } else { '' }; Marker = 'vite.js' }
)
foreach ($entry in $expected) {
    if (-not $entry.Path) { continue }
    $process = Get-CimInstance Win32_Process -Filter "ProcessId = $($entry.Id)" -ErrorAction SilentlyContinue
    $commandLine = if ($process) { [string]$process.CommandLine } else { '' }
    $ownedCommand = $commandLine.Contains($root) -and $commandLine.Contains($entry.Marker)
    if ($process -and $process.ExecutablePath -eq $entry.Path -and $ownedCommand) {
        Stop-Process -Id $entry.Id -Force
    }
}
Remove-Item -LiteralPath $statePath -Force
Write-Output 'My Wardrobe servers stopped.'
