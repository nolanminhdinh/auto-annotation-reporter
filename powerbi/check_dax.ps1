<#!
Compare all 20 KPIs using the running Power BI Desktop engine, not a DAX imitation.
Requires Microsoft's ADOMD client DLL; pass -ClientPath to an existing installation.
No model mutations, refresh, credentials or external network requests are made.
!#>
param(
    [string]$ClientPath = (Join-Path (Split-Path -Parent $PSScriptRoot) 'scratch\adomd\Microsoft.AnalysisServices.AdomdClient.dll'),
    [string]$SourceFolder = (Join-Path (Split-Path -Parent $PSScriptRoot) 'data\processed'),
    [string]$Port,
    [string]$Catalog,
    [string]$OutputPath = (Join-Path (Split-Path -Parent $PSScriptRoot) 'reports\POWERBI_DAX_RECONCILIATION.json')
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $ClientPath)) { throw 'Provide -ClientPath to Microsoft.AnalysisServices.AdomdClient.dll and its dependencies.' }
[System.Reflection.Assembly]::LoadFrom($ClientPath) | Out-Null
if (-not $Port) {
    $reportWorkspace = Join-Path $env:USERPROFILE 'Microsoft\Power BI Desktop Store App\AnalysisServicesWorkspaces'
    $reportPortFile = Get-ChildItem -LiteralPath $reportWorkspace -Filter msmdsrv.port.txt -Recurse | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $reportPortFile) { throw 'Open AnnotationReporter in Power BI Desktop first, or pass -Port.' }
    $Port = (Get-Content -LiteralPath $reportPortFile.FullName -Raw -Encoding Unicode).Trim()
}
$reportConnection = [Microsoft.AnalysisServices.AdomdClient.AdomdConnection]::new("Data Source=localhost:$Port")
try {
    $reportConnection.Open()
    if (-not $Catalog) {
        $reportCommand = $reportConnection.CreateCommand()
        $reportCommand.CommandText = 'SELECT [CATALOG_NAME] FROM $SYSTEM.DBSCHEMA_CATALOGS'
        $reportReader = $reportCommand.ExecuteReader()
        $reportCatalogs = @()
        while ($reportReader.Read()) { $reportCatalogs += $reportReader.GetString(0) }
        $reportReader.Close()
        if ($reportCatalogs.Count -ne 1) { throw 'Pass -Catalog to choose the intended model.' }
        $Catalog = $reportCatalogs[0]
    }
    $reportConnection.ChangeDatabase($Catalog)
    $reportPointer = Get-Content -LiteralPath (Join-Path $SourceFolder 'current.json') -Raw | ConvertFrom-Json
    $reportCommand = $reportConnection.CreateCommand()
    $reportCommand.CommandText = 'EVALUATE ROW("LoadedSnapshot", MAX(report_status[source_snapshot]))'
    $reportReader = $reportCommand.ExecuteReader()
    if (-not $reportReader.Read()) { throw 'Desktop returned no snapshot identity.' }
    $loadedSnapshot = if ($reportReader.IsDBNull(0)) { '' } else { [string]$reportReader.GetValue(0) }
    $reportReader.Close()
    if ($loadedSnapshot -ne $reportPointer.snapshot_id) {
        throw 'Desktop has not loaded the current snapshot. Refresh the intended report, then try again (or select its -Port/-Catalog).'
    }
    $reportBundle = Join-Path $SourceFolder $reportPointer.relative_folder
    $reportExpected = @(Import-Csv -LiteralPath (Join-Path $reportBundle 'kpi_reconciliation.csv') -Encoding utf8)
    $reportFields = @()
    foreach ($metric in $reportExpected) {
        if ($metric.metric -notmatch '^[A-Za-z0-9_]+$') { throw 'Unsafe metric name in reconciliation input.' }
        $reportFields += ('"' + $metric.metric + '", [' + $metric.metric + ']')
    }
    $reportCommand = $reportConnection.CreateCommand()
    $reportCommand.CommandText = 'EVALUATE ROW(' + ($reportFields -join ', ') + ')'
    $reportReader = $reportCommand.ExecuteReader()
    if (-not $reportReader.Read()) { throw 'DAX returned no row.' }
    $reportResults = @()
    for ($i = 0; $i -lt $reportExpected.Count; $i++) {
        $expected = if ($reportExpected[$i].expected_value -eq '') { $null } else { [double]::Parse($reportExpected[$i].expected_value, [Globalization.CultureInfo]::InvariantCulture) }
        $actual = if ($reportReader.IsDBNull($i)) { $null } else { [double]$reportReader.GetValue($i) }
        $passed = if ($null -eq $expected -or $null -eq $actual) { ($null -eq $expected) -and ($null -eq $actual) } else { [Math]::Abs($expected - $actual) -le 0.000000001 }
        $reportResults += [PSCustomObject]@{metric=$reportExpected[$i].metric; expected=$expected; actual=$actual; passed=$passed}
    }
    $reportReader.Close()
    $reportResult = [PSCustomObject]@{checked_at=(Get-Date).ToUniversalTime().ToString('o'); snapshot_id=$reportPointer.snapshot_id; loaded_snapshot_id=$loadedSnapshot; catalog=$Catalog; filter_context='Whole snapshot, no report slicers'; tolerance=0.000000001; results=$reportResults}
    $reportResult | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $OutputPath -Encoding utf8
    $reportResults | Format-Table -AutoSize
    if (@($reportResults | Where-Object { -not $_.passed }).Count -gt 0) { throw 'DAX reconciliation failed.' }
    Write-Host "$($reportResults.Count)/$($reportResults.Count) KPIs match Python."
} finally { $reportConnection.Dispose() }
