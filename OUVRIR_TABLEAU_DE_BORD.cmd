@echo off
cd /d "%~dp0"
set "PYTHONPATH=%~dp003_CODE_PYTHON"
set "PYTHON_CONSOLE=%~dp0.venv\Scripts\python.exe"
if not exist "%PYTHON_CONSOLE%" set "PYTHON_CONSOLE=C:\Users\User\Documents\ChatGPT\Parking Intelligent avec CAM RealSense\demo\.venv\Scripts\python.exe"
if not exist "%PYTHON_CONSOLE%" (
  echo Outils Python absents. Lancez INSTALLER_OUTILS.cmd une fois.
  pause
  exit /b 1
)
start "Serveur parking IP7" "%PYTHON_CONSOLE%" -m parking_demo serve --dir "%~dp005_RESULTATS_DEMO" --port 8001
ping 127.0.0.1 -n 3 >nul
start "" "http://127.0.0.1:8001/"
