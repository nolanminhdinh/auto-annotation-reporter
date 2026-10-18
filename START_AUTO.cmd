@echo off
setlocal
if not exist "%~dp0.venv\Scripts\python.exe" (
  echo Create .venv with Python 3.10+ first. See powerbi/README.md.
  pause
  exit /b 1
)
"%~dp0.venv\Scripts\python.exe" -X utf8 -B "%~dp0src\auto_desktop.py" --setup --open-report
set "autoExitCode=%ERRORLEVEL%"
if not "%autoExitCode%"=="0" pause
endlocal & exit /b %autoExitCode%
