@echo off
setlocal
cd /d "%~dp0"

if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" "%~dp0auto_sync.py"
    goto :end
)

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 "%~dp0auto_sync.py"
    goto :end
)

where python >nul 2>nul
if %errorlevel%==0 (
    python "%~dp0auto_sync.py"
    goto :end
)

echo No se encontro Python en PATH.
echo Instala Python o anade el ejecutable al PATH.
:end
pause
