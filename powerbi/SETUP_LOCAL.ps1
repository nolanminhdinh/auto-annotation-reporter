$ErrorActionPreference = 'Stop'
$setupRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $setupRoot
try {
    $setupPython = Join-Path $setupRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $setupPython)) {
        if (Get-Command py -ErrorAction SilentlyContinue) { & py -3 -m venv .venv }
        elseif (Get-Command python -ErrorAction SilentlyContinue) { & python -m venv .venv }
        else { throw 'Install Python 3.10 or newer, then run this script again.' }
        if ($LASTEXITCODE -ne 0) { throw 'Unable to create the Python virtual environment.' }
    }
    & $setupPython -m pip install -r requirements-runtime.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
    Write-Host 'Local runtime ready. Run .\powerbi\RUN_DEMO.ps1 -OpenReport.'
} finally { Pop-Location }
