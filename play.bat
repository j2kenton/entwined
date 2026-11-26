@echo off
rem Play Entwined. Options are passed on, e.g.  play --hero kael
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 -m game %*
    goto :eof
)
where python >nul 2>nul
if %errorlevel%==0 (
    python -m game %*
    goto :eof
)
echo Entwined needs Python 3: https://www.python.org/downloads/
pause
