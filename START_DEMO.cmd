@echo off
setlocal
if not exist "%~dp0.venv\Scripts\python.exe" (
  echo Create .venv with Python 3.10+ and install requirements-runtime.txt first.
  pause
  exit /b 1
)
"%~dp0.venv\Scripts\python.exe" -X utf8 -B "%~dp0src\desktop_demo.py" --open-report
set "demoExitCode=%ERRORLEVEL%"
if not "%demoExitCode%"=="0" pause
endlocal & exit /b %demoExitCode%
