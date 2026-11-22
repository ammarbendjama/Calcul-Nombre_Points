# Version Windows

## Le plus simple : `NombrePoints.exe` (tout intégré, double-clic)

Un exécutable **graphique et autonome** est construit automatiquement par
GitHub Actions à chaque push dans le dépôt (moteur OCR embarqué, aucune
installation : ni Python, ni Tesseract).

1. Ouvrez le dépôt → onglet **Actions** → workflow **Build Windows EXE**.
2. Cliquez sur l'exécution la plus récente réussie → section **Artifacts**.
3. Téléchargez `NombrePoints-Windows.zip`, décompressez-le.
4. **Double-cliquez sur `NombrePoints.exe`** :
   - bouton *Choisir la vidéo…* → sélectionnez la vidéo des copies
   - bouton *Analyser* → progression + journal
   - à la fin : table des copies avec leurs points, et bouton
     *Ouvrir les résultats* (dossier `resultats\` à côté de la vidéo : CSV,
     JSON, pages annotées).

Le premier démarrage peut prendre quelques secondes (décompression).

## En ligne de commande (optionnel)

```bat
:: avec le lanceur (installe Python + dépendances au premier lancement)
windows\lancer.bat ma_video.mp4 -o resultats

:: ou avec l'exe
NombrePoints.exe ma_video.mp4 -o resultats
```

Moteurs complémentaires :
- `--moteur rapidocr` : OCR intégré, aucune installation (par défaut de l'interface)
- `--moteur pytesseract` : nécessite `choco install tesseract-ocr`
- `--moteur easyocr` : `pip install easyocr` (meilleur sur l'écriture manuscrite)

## Compiler l'exe soi-même

```bat
py -m pip install -r requirements.txt pyinstaller
py -m PyInstaller windows\NombrePoints.spec --distpath dist
```
