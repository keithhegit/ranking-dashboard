$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $Root "scripts_common.ps1")

& (Join-Path $Root "setup.ps1")
$Browser = Find-BrowserExecutable
$Profile = Join-Path $Root "runtime\browser_profile"
Start-ProjectBrowser $Browser $Profile

Write-Host ""
Write-Host "Sensor Tower has opened in a dedicated browser profile." -ForegroundColor Cyan
Write-Host "Log in manually, verify that the rankings page is accessible, then close this window."
Write-Host "The login session stays only on this computer under runtime\browser_profile."
Read-Host "Press Enter after login is complete"

