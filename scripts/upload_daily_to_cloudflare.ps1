param(
    [Parameter(Mandatory = $true)]
    [string] $WorkerUrl,
    [Parameter(Mandatory = $true)]
    [string] $IngestToken,
    [string] $Date = (Get-Date -Format "yyyyMMdd")
)

$ErrorActionPreference = "Stop"

$Project = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$CsvPath = Join-Path $Project "output\sensor_tower_multi_product_multi_country_$Date.csv"
if (-not (Test-Path -LiteralPath $CsvPath)) {
    throw "Daily CSV not found: $CsvPath"
}

$rows = Import-Csv -LiteralPath $CsvPath | ForEach-Object {
    [ordered]@{
        brand = $_.brand
        package = $_.package
        country = $_.country
        tooltip_date = $_.tooltip_date
        revenue_rank_tools = $_.revenue_rank_tools
        status = $_.status
        status_detail = $_.status_detail
        source_url = $_.source_url
        crawl_time = $_.crawl_time
        raw_tooltip_text = $_.raw_tooltip_text
        screenshot_path = $_.screenshot_path
    }
}

$dateIso = "{0}-{1}-{2}" -f $Date.Substring(0, 4), $Date.Substring(4, 2), $Date.Substring(6, 2)
$payload = @{
    date = $dateIso
    source = "local-windows-scraper"
    rows = @($rows)
} | ConvertTo-Json -Depth 8

$endpoint = $WorkerUrl.TrimEnd("/") + "/api/ingest"
$response = Invoke-RestMethod -Method Post -Uri $endpoint -ContentType "application/json; charset=utf-8" `
    -Headers @{ Authorization = "Bearer $IngestToken"; "User-Agent" = "ranking-dashboard-runner/1.0" } -Body $payload

$response | ConvertTo-Json -Depth 8
