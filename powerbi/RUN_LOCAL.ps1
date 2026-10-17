param(
    [ValidateSet('offline', 'live')][string]$Mode = 'offline',
    [string]$Snapshot = 'sample_data/powerbi_demo',
    [string]$Operations,
    [string]$TeamReports,
    [string]$FrameSize,
    [string]$Session = 'Mentor report',
    [switch]$CheckOnly
)
$ErrorActionPreference = 'Stop'
$reportRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $reportRoot
try {
    $reportPython = Join-Path $reportRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $reportPython)) { throw 'Create .venv and install requirements-runtime.txt first.' }
    if ($CheckOnly -or $Mode -eq 'live') {
        $readinessArguments = @('-X', 'utf8', '-B', '-m', 'src.desktop_readiness')
        if ($Mode -eq 'live') { $readinessArguments += '--require-live' }
        & $reportPython @readinessArguments
        if ($LASTEXITCODE -ne 0) { throw 'Live configuration incomplete. Read next_actions above; no API requests were sent.' }
        if ($CheckOnly) { return }
    }
    $reportArguments = @('-X', 'utf8', '-B', 'src/main.py', '--mode', $Mode, '--session', $Session, '--llm-summary', '--notify', 'preview')
    if ($Mode -eq 'offline') { $reportArguments += @('--snapshot', $Snapshot) }
    if ($Operations) { $reportArguments += @('--operations', $Operations) }
    if ($TeamReports) { $reportArguments += @('--team-reports', $TeamReports) }
    if ($FrameSize) { $reportArguments += @('--frame-size', $FrameSize) }
    & $reportPython @reportArguments
    if ($LASTEXITCODE -ne 0) { throw 'Publication failed. Read the pipeline error before refreshing Power BI.' }
    Write-Host 'Published. Open powerbi/AnnotationReporter_Desktop.pbix (or project_desktop/AnnotationReporter.pbip), select Refresh, then Save.'
} finally { Pop-Location }
