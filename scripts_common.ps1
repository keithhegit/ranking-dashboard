function Find-BrowserExecutable {
    $candidates = @(
        "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
        "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
        "$env:LOCALAPPDATA\Microsoft\Edge\Application\msedge.exe",
        "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
        "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
        "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
    )
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate)) { return $candidate }
    }
    throw "Microsoft Edge or Google Chrome was not found."
}

function Test-CDP {
    try {
        $response = Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:9222/json/version" -TimeoutSec 5
        return $response.StatusCode -eq 200
    } catch { return $false }
}

function Stop-ProjectBrowser([string] $Profile) {
    Get-CimInstance Win32_Process -Filter "name='msedge.exe' OR name='chrome.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like "*remote-debugging-port=9222*" -or $_.CommandLine -like "*$Profile*" } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 2
}

function Start-ProjectBrowser([string] $Browser, [string] $Profile) {
    if (Test-CDP) { return }
    New-Item -ItemType Directory -Force -Path $Profile | Out-Null
    Start-Process -FilePath $Browser -ArgumentList @(
        "--remote-debugging-port=9222",
        "--user-data-dir=$Profile",
        "--no-first-run",
        "--no-default-browser-check",
        "https://app.sensortower.com/"
    )
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 2
        if (Test-CDP) { return }
    }
    throw "Browser debugging port 9222 did not become ready."
}
