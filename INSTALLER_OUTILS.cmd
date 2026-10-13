@echo off
cd /d "%~dp0"
echo Installation des bibliotheques Python dans ce dossier...
py -3.13 -m venv .venv
if errorlevel 1 goto erreur
"%~dp0.venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto erreur
"%~dp0.venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto erreur
echo.
echo Installation terminee. Double-cliquez OUVRIR_ATELIER.cmd ou OUVRIR_TABLEAU_DE_BORD.cmd.
pause
exit /b 0
:erreur
echo.
echo Installation interrompue. Verifiez Python 3.13 et la connexion Internet.
pause
exit /b 1
