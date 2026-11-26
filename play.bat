@echo off
rem Play the Entwined prototype. Options are passed on, e.g.  play --sixel
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 prototype\play.py %*
    goto :eof
)
where python >nul 2>nul
if %errorlevel%==0 (
    python prototype\play.py %*
    goto :eof
)
echo Entwined needs Python 3: https://www.python.org/downloads/
pause
