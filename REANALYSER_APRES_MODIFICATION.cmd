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
set "ZONES=%~dp002_POLYGONES\places_18_essai_manuel.json"
if not exist "%ZONES%" (
  echo Aucun essai enregistre. Ouvrez OUVRIR_ATELIER.cmd puis enregistrez les polygones.
  pause
  exit /b 1
)
echo Nouvelle analyse de dix minutes avec les polygones modifies...
"%PYTHON_CONSOLE%" -m parking_demo analyze --video "%~dp001_VIDEO_SOURCE\video_ip7_10_minutes.mp4" --zones "%ZONES%" --out-dir "%~dp008_RESULTATS_APRES_MODIFICATION" --model "%~dp007_MODELE_YOLO\yolo26n.pt" --stride 1 --stable-sec 8 --free-stable-sec 8 --recording-start 09:44:46
if errorlevel 1 (
  echo L'analyse a echoue. Les resultats initiaux sont toujours dans 05_RESULTATS_DEMO.
  pause
  exit /b 1
)
start "Serveur resultat modifie" "%PYTHON_CONSOLE%" -m parking_demo serve --dir "%~dp008_RESULTATS_APRES_MODIFICATION" --port 8002
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:8002/"
echo Nouvelle analyse terminee. Les fichiers sont dans 08_RESULTATS_APRES_MODIFICATION.
pause
