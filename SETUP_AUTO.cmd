@echo off
call "%~dp0START_AUTO.cmd" --setup-only
exit /b %ERRORLEVEL%
