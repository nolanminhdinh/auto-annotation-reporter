param([switch]$RebuildProject, [switch]$OpenReport, [switch]$Setup)
$ErrorActionPreference = 'Stop'
$reportRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $reportRoot
try {
    if ($Setup) { & (Join-Path $PSScriptRoot 'SETUP_LOCAL.ps1') }
    $reportPython = Join-Path $reportRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $reportPython)) { throw 'Create .venv and install requirements-runtime.txt first (see powerbi/README.md).' }
    $demoArguments = @('-X', 'utf8', '-B', 'src/desktop_demo.py')
    if ($RebuildProject) { $demoArguments += '--rebuild-project' }
    if ($OpenReport) { $demoArguments += '--open-report' }
    & $reportPython @demoArguments
    if ($LASTEXITCODE -ne 0) { throw "Demo stopped (exit $LASTEXITCODE). Read the error and run receipt above." }
} finally { Pop-Location }
