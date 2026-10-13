@echo off
cd /d "%~dp0\09_HEBERGEMENT_DEMO"
if not exist "..\.venv\Scripts\python.exe" (
  echo Python local introuvable. Lancez INSTALLER_OUTILS.cmd.
  pause
  exit /b 1
)
start "" "http://127.0.0.1:8010/"
"..\.venv\Scripts\python.exe" run_local.py
pause
