# Nombre de points de la copie

Application qui calcule automatiquement le **nombre de points de chaque copie
double d'examen** à partir d'une **vidéo** (film du correcteur passant les
copies devant la caméra).

| Version | Dossier | Guide |
|---|---|---|
| **Windows** (interface graphique, `.exe` tout-en-un OCR intégré, construit par GitHub Actions) | [`windows/`](windows/) | [windows/INSTALL.md](windows/INSTALL.md) |
| **Android & iOS** (application web installable, OCR dans le navigateur) | [`mobile/`](mobile/) | [mobile/INSTALL.md](mobile/INSTALL.md) |

## Fonctionnement

1. **Extraction** : la vidéo est analysée image par image ; la même page
   restée devant la caméra n'est gardée qu'une seule fois.
2. **Regroupement** : les pages successives sont regroupées en copies
   (une nouvelle copie commence quand la page change fortement).
3. **Détection** : les zones d'écriture (notes manuscrites comme `1,5/2`,
   `0,5/1`, `3/4`...) sont repérées sur chaque page.
4. **Reconnaissance** : chaque zone est lue par OCR (Tesseract ou EasyOCR)
   et les points obtenus sont extraits.
5. **Synthèse** : total de points par copie, rapport CSV/JSON et pages
   annotées (zones surlignées avec les points lus).

## Installation

```bash
python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -r requirements.txt
```

Moteur OCR (choisir un moteur) :

- **Tesseract** (par défaut) : `sudo apt install tesseract-ocr` (Linux) ou
  `choco install tesseract` (Windows), puis `pip install pytesseract`.
- **EasyOCR** (meilleur sur l'écriture manuscrite) : `pip install easyocr`
  puis lancer l'app avec `--moteur easyocr`.

## Utilisation

```bash
python main.py ma_video.mp4
```

Résultats dans `resultats/` :

- `report.csv` — détail des notes et TOTAL par copie (format `;`)
- `report.json` — résultats complets (zones, confiance, coordonnées)
- `pages/` — copies annotées avec les points reconnus

Héberger la page récapitulative dans le navigateur :

```bash
python -m http.server 8000 --directory resultats
# puis ouvrir http://localhost:8000 (ouvre report.json/pages)
```

Options utiles :

| Option | Effet |
|---|---|
| `--moteur easyocr` | OCR neuronal, meilleur sur l'écriture manuscrite |
| `--accepter-entiers` | lire aussi les notes entières seules (`2`, `3`...) |
| `--pages-par-copie 2` | forcer 2 pages par copie (copie double recto/verso) |
| `--pas-echantillon N` | 1 image analysée tous les N (défaut 5) |
| `--seuil-nouvelle-copie X` | sensibilité du découpage en copies (défaut 0.40) |
| `--confiance-min X` | ignorer les notes lues avec peu de confiance (défaut 0.5) |

## Vidéo de démonstration

```bash
python scripts/make_demo_video.py demo.mp4
python main.py demo.mp4 -o resultats
```

## Limites connues

- L'écriture **manuscrite** est difficile : EasyOCR donne de meilleurs
  résultats que Tesseract. Vérifiez le détail dans `report.csv` et les
  pages annotées, et corrigez au besoin.
- Les pages doivent être vues bien à plat, sans ombre ni flou important.
- `12` peut être lu à la place de `1,5` : la virgule manuscrite est parfois
  discrète. Le rapport conserve le texte brut lu (`texte_lu`) pour vérifier.

## Tests

```bash
python -m pytest tests/ -v
```
