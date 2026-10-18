@echo off
setlocal
pushd "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -X utf8 -B "%~dp0tools\desktop_bootstrap.py" %*
) else (
  where python >nul 2>nul
  if errorlevel 1 (
    echo Install Python 3.10+ and enable its launcher or PATH, then rerun this file.
    popd
    pause
    exit /b 1
  )
  python -X utf8 -B "%~dp0tools\desktop_bootstrap.py" %*
)
set "autoExitCode=%ERRORLEVEL%"
popd
if not "%autoExitCode%"=="0" pause
endlocal & exit /b %autoExitCode%
