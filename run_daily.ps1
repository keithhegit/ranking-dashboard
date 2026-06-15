param(
    [string] $Date = (Get-Date -Format "yyyyMMdd"),
    [string] $DateIso = (Get-Date -Format "yyyy-MM-dd"),
    [int] $BatchTimeoutSeconds = 600,
    [int] $RateLimitCooldownSeconds = 300,
    [switch] $SkipDashboard,
    [string] $CloudflareWorkerUrl = $env:CLOUDFLARE_WORKER_URL,
    [string] $CloudflareIngestToken = $env:CLOUDFLARE_INGEST_TOKEN,
    [switch] $SkipCloudflareUpload
)

$ErrorActionPreference = "Continue"

$Project = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $Project "scripts_common.ps1")
$Python = Join-Path $Project ".venv\Scripts\python.exe"
$Edge = Find-BrowserExecutable
$Profile = Join-Path $Project "runtime\browser_profile"
$Wrapper = Join-Path $Project "sensor_tower_focus_fast.py"
$Output = Join-Path $Project "output"
$ProjectOutput = Join-Path $Project "output"
$BatchDir = Join-Path $Output "daily_all_$Date"

$Products = @("ugphone", "ldcloud", "redfinger", "vsphone")
$CountryOrder = @("TH", "VN", "PH", "BR", "TR", "MY", "ID", "HK", "TW", "KR", "US", "MX", "SG", "JP", "PL", "DE", "GB", "IN", "IT", "FR")
$CountryChunks = @(
    @("TH", "VN", "PH", "BR"),
    @("TR", "MY", "ID", "HK"),
    @("TW", "KR", "US", "MX"),
    @("SG", "JP", "PL", "DE"),
    @("GB", "IN", "IT", "FR")
)

New-Item -ItemType Directory -Force -Path $Output, $ProjectOutput, $BatchDir | Out-Null

function Write-RunLog([string] $Message) {
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    $line | Tee-Object -FilePath (Join-Path $BatchDir "daily_all.log") -Append
}

function Stop-CDPEdge {
    Stop-ProjectBrowser $Profile
}

function Ensure-CDP {
    if (-not (Test-CDP)) { Write-RunLog "Starting browser with project profile: $Profile" }
    Start-ProjectBrowser $Edge $Profile
}

function Invoke-BatchProcess([string] $Product, [string[]] $Countries, [string] $Name) {
    Ensure-CDP
    $env:ST_PRODUCTS = $Product
    $env:ST_COUNTRIES = ($Countries -join ",")

    $stdout = Join-Path $BatchDir "run_$Name.out.log"
    $stderr = Join-Path $BatchDir "run_$Name.err.log"
    Remove-Item -LiteralPath $stdout, $stderr -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath (Join-Path $Output "sensor_tower_multi_product_multi_country_$Date.csv") -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath (Join-Path $Output "sensor_tower_multi_product_summary_$Date.csv") -Force -ErrorAction SilentlyContinue
    Write-RunLog "Batch start: $Name product=$Product countries=$($Countries -join ',')"

    $proc = Start-Process -FilePath $Python -ArgumentList @($Wrapper) -WorkingDirectory $Project `
        -RedirectStandardOutput $stdout -RedirectStandardError $stderr -NoNewWindow -PassThru

    $timedOut = $false
    try {
        Wait-Process -Id $proc.Id -Timeout $BatchTimeoutSeconds -ErrorAction Stop
    } catch {
        $timedOut = $true
        Write-RunLog "Batch timeout: $Name after ${BatchTimeoutSeconds}s; killing process $($proc.Id)"
        try { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue } catch {}
        Start-Sleep -Seconds 2
    }

    if (-not $timedOut) { try { $proc.Refresh() } catch {} }
    $exitCode = if ($timedOut) { 124 } else { $proc.ExitCode }
    $detail = Join-Path $Output "sensor_tower_multi_product_multi_country_$Date.csv"
    $summary = Join-Path $Output "sensor_tower_multi_product_summary_$Date.csv"
    if (Test-Path -LiteralPath $detail) {
        Copy-Item -LiteralPath $detail -Destination (Join-Path $BatchDir "detail_$Name.csv") -Force
    }
    if (Test-Path -LiteralPath $summary) {
        Copy-Item -LiteralPath $summary -Destination (Join-Path $BatchDir "summary_$Name.csv") -Force
    }
    Write-RunLog "Batch end: $Name exit=$exitCode"
    return $exitCode
}

function Get-BadCountries([string] $DetailPath) {
    if (-not (Test-Path -LiteralPath $DetailPath)) { return @() }
    $rows = @(Import-Csv -LiteralPath $DetailPath)
    return @(
        $rows |
            Where-Object { $_.status -in @("RATE_LIMITED", "PAGE_LOAD_FAILED") } |
            Select-Object -ExpandProperty country -Unique
    )
}

function Test-DetailHasRateLimit([string] $DetailPath) {
    if (-not (Test-Path -LiteralPath $DetailPath)) { return $false }
    return [bool](@(Import-Csv -LiteralPath $DetailPath | Where-Object { $_.status -eq "RATE_LIMITED" }).Count)
}

if (-not (Test-Path -LiteralPath $Wrapper)) {
    throw "Wrapper not found: $Wrapper"
}
if (-not (Test-Path -LiteralPath $Python)) {
    throw "Python environment not found. Run FIRST_RUN_LOGIN.bat first."
}

Write-RunLog "Daily full scrape start date=$Date products=$($Products -join ',') countries=$($CountryOrder -join ',')"
Ensure-CDP

$batchNo = 0
foreach ($product in $Products) {
    foreach ($chunk in $CountryChunks) {
        $batchNo += 1
        $name = "{0:D2}_{1}_{2}" -f $batchNo, $product, ($chunk -join "-")
        $code = Invoke-BatchProcess $product $chunk $name
        $detailPath = Join-Path $BatchDir "detail_$name.csv"
        $bad = @(Get-BadCountries $detailPath)
        if ($code -eq 124 -or $bad.Count -gt 0) {
            Write-RunLog "Retry needed for $name code=$code bad=$($bad -join ',')"
            Stop-CDPEdge
            if (Test-DetailHasRateLimit $detailPath) {
                Start-Sleep -Seconds $RateLimitCooldownSeconds
            } elseif ($code -eq 124) {
                Start-Sleep -Seconds 30
            }
            Ensure-CDP
            $retryCountries = if ($bad.Count -gt 0) { $bad } else { $chunk }
            $retryName = "retry_$name"
            Invoke-BatchProcess $product $retryCountries $retryName | Out-Null
        }
    }
}

$statusScore = @{
    "SUCCESS" = 5
    "PARTIAL_SUCCESS" = 4
    "RANK_CAPTURE_FAILED" = 2
    "RATE_LIMITED" = 1
    "PAGE_LOAD_FAILED" = 1
}

function Get-DateScore([string] $Value) {
    if ([string]::IsNullOrWhiteSpace($Value)) { return 0 }
    try { return [int64]([datetime]::Parse($Value).ToString("yyyyMMdd")) } catch { return 0 }
}

$best = @{}
$detailFiles = Get-ChildItem -LiteralPath $BatchDir -Filter "detail_*.csv" | Sort-Object LastWriteTime
foreach ($file in $detailFiles) {
    foreach ($row in @(Import-Csv -LiteralPath $file.FullName)) {
        if (-not $row.brand -or -not $row.country) { continue }
        $key = "$($row.brand)|$($row.country)"
        $row | Add-Member -NotePropertyName batch_file -NotePropertyValue $file.Name -Force
        $scoreStatus = if ($statusScore.ContainsKey($row.status)) { $statusScore[$row.status] } else { 0 }
        $rankScore = if ($row.revenue_rank_tools -match "^\d+$") { 1000000 - [int]$row.revenue_rank_tools } else { 0 }
        $score = ($scoreStatus * 1000000000000) + ((Get-DateScore $row.tooltip_date) * 100000) + $rankScore
        if (-not $best.ContainsKey($key) -or $score -gt $best[$key].score) {
            $best[$key] = [pscustomobject]@{ score = $score; row = $row }
        }
    }
}

$brandIndex = @{ ugphone = 0; ldcloud = 1; redfinger = 2; vsphone = 3 }
$countryIndex = @{}
for ($i = 0; $i -lt $CountryOrder.Count; $i++) { $countryIndex[$CountryOrder[$i]] = $i }

$merged = foreach ($brand in $Products) {
    foreach ($country in $CountryOrder) {
        $key = "$brand|$country"
        if ($best.ContainsKey($key)) {
            $best[$key].row
        } else {
            [pscustomobject]@{
                brand = $brand; package = ""; country = $country; tooltip_date = "";
                app_name = ""; revenue_rank_tools = ""; revenue_rank_apps = ""; top_free_rank_tools = "";
                source_url = ""; crawl_time = $DateIso; status = "MISSING"; status_detail = "not found in batch outputs";
                error_message = ""; candidate_tooltip_dates = ""; candidate_count = ""; selected_tooltip_date = "";
                page_loaded_screenshot = ""; final_hover_screenshot = ""; retry_count = ""; screenshot_path = "";
                selected_candidate_index = ""; selected_candidate_raw_text = ""; raw_tooltip_text = "";
                selected_candidate_x = ""; selected_candidate_y = ""; all_candidates_json = ""; batch_file = "";
            }
        }
    }
}

$merged = @($merged | Sort-Object @{ Expression = { $brandIndex[$_.brand] } }, @{ Expression = { $countryIndex[$_.country] } })

# Data policy: only record Sensor Tower "收入排行 - 工具" as the ranking signal.
# Other tooltip metrics may be visible, but must not enter the stored dataset or dashboard logic.
foreach ($row in $merged) {
    if ($row.PSObject.Properties.Name -contains "revenue_rank_apps") {
        $row.revenue_rank_apps = ""
    }
    if ($row.PSObject.Properties.Name -contains "top_free_rank_tools") {
        $row.top_free_rank_tools = ""
    }
}

$detailOut = Join-Path $Output "sensor_tower_multi_product_multi_country_$Date.csv"
$summaryOut = Join-Path $Output "sensor_tower_multi_product_summary_$Date.csv"
$fullDetailOut = Join-Path $Output "sensor_tower_multi_product_multi_country_full80_$Date.csv"
$fullSummaryOut = Join-Path $Output "sensor_tower_multi_product_summary_full80_$Date.csv"

$merged | Export-Csv -LiteralPath $detailOut -NoTypeInformation -Encoding UTF8
$merged | Export-Csv -LiteralPath $fullDetailOut -NoTypeInformation -Encoding UTF8
$merged |
    Select-Object brand,country,tooltip_date,revenue_rank_tools,status,status_detail,batch_file |
    Export-Csv -LiteralPath $summaryOut -NoTypeInformation -Encoding UTF8
$merged |
    Select-Object brand,country,tooltip_date,revenue_rank_tools,status,status_detail,batch_file |
    Export-Csv -LiteralPath $fullSummaryOut -NoTypeInformation -Encoding UTF8

Copy-Item -LiteralPath $detailOut -Destination (Join-Path $ProjectOutput "sensor_tower_multi_product_multi_country_$Date.csv") -Force
Copy-Item -LiteralPath $summaryOut -Destination (Join-Path $ProjectOutput "sensor_tower_multi_product_summary_$Date.csv") -Force
Copy-Item -LiteralPath $fullDetailOut -Destination (Join-Path $ProjectOutput "sensor_tower_multi_product_multi_country_full80_$Date.csv") -Force
Copy-Item -LiteralPath $fullSummaryOut -Destination (Join-Path $ProjectOutput "sensor_tower_multi_product_summary_full80_$Date.csv") -Force

if (-not $SkipCloudflareUpload) {
    if ($CloudflareWorkerUrl -and $CloudflareIngestToken) {
        $uploadScript = Join-Path $Project "scripts\upload_daily_to_cloudflare.ps1"
        if (-not (Test-Path -LiteralPath $uploadScript)) {
            throw "Cloudflare upload script not found: $uploadScript"
        }
        Write-RunLog "Cloudflare upload start: $CloudflareWorkerUrl"
        $global:LASTEXITCODE = 0
        & $uploadScript -WorkerUrl $CloudflareWorkerUrl -IngestToken $CloudflareIngestToken -Date $Date
        if ($LASTEXITCODE -ne 0) {
            throw "Cloudflare upload failed with exit code $LASTEXITCODE"
        }
        Write-RunLog "Cloudflare upload finished"
    } elseif ($CloudflareWorkerUrl -or $CloudflareIngestToken) {
        throw "Cloudflare upload requires both CloudflareWorkerUrl and CloudflareIngestToken."
    } else {
        Write-RunLog "Cloudflare upload skipped: CloudflareWorkerUrl and CloudflareIngestToken are not configured"
    }
}

if (-not $SkipDashboard) {
    & $Python (Join-Path $Project "dashboard_builder.py")
    $BuiltDashboard = Join-Path $ProjectOutput "dashboard.html"
    if (Test-Path -LiteralPath $BuiltDashboard) {
        Copy-Item -LiteralPath $BuiltDashboard -Destination (Join-Path $Project "dashboard.html") -Force
        Write-RunLog "Dashboard synced to project root"
    } else {
        Write-RunLog "Dashboard build finished but output dashboard was not found: $BuiltDashboard"
    }
}

Write-RunLog "Daily full scrape finished rows=$($merged.Count)"
$merged | Group-Object brand | Select-Object Name,Count | Format-Table -AutoSize
$merged | Group-Object status | Select-Object Name,Count | Format-Table -AutoSize
Write-Host "Dashboard: $(Join-Path $Project 'dashboard.html')"

if (-not $SkipDashboard) {
    $serverReady = $false
    try {
        $serverReady = (Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8765/dashboard.html" -TimeoutSec 3).StatusCode -eq 200
    } catch {}
    if (-not $serverReady) {
        Start-Process -FilePath $Python -ArgumentList @("-m", "http.server", "8765", "--bind", "127.0.0.1") `
            -WorkingDirectory $Project -WindowStyle Hidden
        Start-Sleep -Seconds 2
    }
    Start-Process "http://127.0.0.1:8765/dashboard.html?ts=$([DateTimeOffset]::Now.ToUnixTimeMilliseconds())"
}
