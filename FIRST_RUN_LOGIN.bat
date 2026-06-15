@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0first_run_login.ps1"
if errorlevel 1 (
  echo.
  echo Setup or login startup failed. Review the message above.
  pause
  exit /b 1
)
echo.
echo Login setup is complete. Next time run RUN_DAILY.bat.
pause

