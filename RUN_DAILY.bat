@echo off
setlocal
cd /d "%~dp0"
if not exist "%~dp0.venv\Scripts\python.exe" (
  echo First-time setup is required.
  call "%~dp0FIRST_RUN_LOGIN.bat"
  if errorlevel 1 exit /b 1
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_daily.ps1" %*
if errorlevel 1 (
  echo.
  echo Daily run failed. Check logs\daily_all_YYYYMMDD\daily_all.log.
  pause
  exit /b 1
)
echo.
echo Daily run completed.
pause

