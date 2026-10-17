# Optional native Tabular validation. Use Power BI Desktop Refresh for DAX evaluation.
param([string]$ModelPath = (Join-Path $PSScriptRoot 'project\AnnotationReporter.SemanticModel\model.bim'))
$ErrorActionPreference = 'Stop'
$reportModel = Get-Content -LiteralPath $ModelPath -Raw | ConvertFrom-Json
$reportTables = @{}
foreach ($table in $reportModel.model.tables) {
    $reportTables[$table.name] = @($table.columns.name)
}
foreach ($relation in $reportModel.model.relationships) {
    if ($reportTables[$relation.fromTable] -notcontains $relation.fromColumn) { throw "Missing source column in $($relation.name)" }
    if ($reportTables[$relation.toTable] -notcontains $relation.toColumn) { throw "Missing target column in $($relation.name)" }
}
Write-Host "Model structure: $($reportTables.Count) tables, $($reportModel.model.relationships.Count) relationships."
