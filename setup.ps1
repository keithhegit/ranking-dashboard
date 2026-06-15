$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Venv = Join-Path $Root ".venv"

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python launcher was not found. Install Python 3.13 (64-bit) from python.org first."
}

& py -3.13 -c "import sys; assert sys.version_info[:2] == (3, 13)"
if ($LASTEXITCODE -ne 0) { throw "Python 3.13 is required." }

if (-not (Test-Path -LiteralPath (Join-Path $Venv "Scripts\python.exe"))) {
    & py -3.13 -m venv $Venv
}

$Python = Join-Path $Venv "Scripts\python.exe"
& $Python -m pip install --upgrade pip
& $Python -m pip install -r (Join-Path $Root "requirements.txt")

$Directories = @(
    (Join-Path $Root "output"),
    (Join-Path $Root "logs"),
    (Join-Path $Root "screenshots"),
    (Join-Path $Root "runtime")
)
New-Item -ItemType Directory -Force -Path $Directories | Out-Null

Write-Host "Setup completed." -ForegroundColor Green
