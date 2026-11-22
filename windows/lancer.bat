@echo off
rem "Nombre de points de la copie" sous Windows, sans compilation.
rem Premier lancement : installe l'environnement Python automatiquement.
setlocal
cd /d "%~dp0.."

where py >nul 2>nul
if errorlevel 1 (
    echo [ERREUR] Python n'est pas installe. Installez-le depuis https://www.python.org/downloads/
    echo          en cochant "Add python.exe to PATH".
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/2] Premiere installation (environ 2 minutes)...
    py -m venv .venv
    ".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERREUR] Installation impossible. Verifiez votre connexion internet.
        pause
        exit /b 1
    )
)

echo [2/2] Lancez : .venv\Scripts\python.exe main.py votre_video.mp4
".venv\Scripts\python.exe" main.py %*
pause
