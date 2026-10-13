@echo off
cd /d "%~dp0"
set "PYTHONPATH=%~dp003_CODE_PYTHON"
set "PYTHON_VISUEL=%~dp0.venv\Scripts\pythonw.exe"
if not exist "%PYTHON_VISUEL%" set "PYTHON_VISUEL=C:\Users\User\Documents\ChatGPT\Parking Intelligent avec CAM RealSense\demo\.venv\Scripts\pythonw.exe"
if not exist "%PYTHON_VISUEL%" (
  echo Outils Python absents. Lancez INSTALLER_OUTILS.cmd une fois.
  pause
  exit /b 1
)
start "Atelier polygones et YOLO" "%PYTHON_VISUEL%" -m parking_demo.manual_lab
