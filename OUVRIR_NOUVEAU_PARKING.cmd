@echo off
cd /d "%~dp0"
set "PYTHONPATH=%~dp003_CODE_PYTHON"
set "PYTHON_CONSOLE=%~dp0.venv\Scripts\python.exe"
if not exist "%PYTHON_CONSOLE%" set "PYTHON_CONSOLE=python.exe"
start "Serveur Nouveau Parking" "%PYTHON_CONSOLE%" -m parking_demo serve --dir "%~dp008_RESULTATS_NOUVELLE_VIDEO" --port 8002
ping 127.0.0.1 -n 3 >nul
start "" "http://127.0.0.1:8002/"
