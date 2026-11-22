# Version Windows

Deux façons d'utiliser « Nombre de points de la copie » sous Windows.

## 1. Le plus simple : le fichier `NombrePoints.exe`

Un `.exe` autonome (aucune installation) est construit automatiquement par
GitHub Actions à chaque push dans le dépôt :

1. Ouvrez le dépôt → onglet **Actions** → workflow **Build Windows EXE**.
2. Cliquez sur l'exécution la plus récente → section **Artifacts**.
3. Téléchargez `NombrePoints-Windows.zip`, décompressez-le.
4. Dans une invite de commandes, dans le dossier de la vidéo :

```bat
NombrePoints.exe ma_video.mp4 -o resultats
```

> **Important** : le moteur OCR Tesseract doit être installé à part :
> `choco install tesseract` (ou téléchargez l'installateur
> https://github.com/UB-Mannheim/tesseract/wiki et ajoutez-le au PATH).
> L'option `--moteur easyocr` n'a pas besoin de Tesseract mais l'exe embarque
> alors un modèle volumineux : préférez l'installation du lanceur ci-dessous.

## 2. Le lanceur `lancer.bat` (avec Python)

1. Installez Python : https://www.python.org/downloads/ en cochant
   **Add python.exe to PATH**.
2. Installez Tesseract : `choco install tesseract-ocr`
3. Double-cliquez sur `lancer.bat` ou dans une invite de commandes :

```bat
windows\lancer.bat ma_video.mp4 -o resultats
```

La première exécution crée l'environnement et installe les dépendances.

## Compiler l'exe soi-même

```bat
py -m pip install -r requirements.txt pyinstaller
py -m pyinstaller windows\NombrePoints.spec --distpath dist
```
