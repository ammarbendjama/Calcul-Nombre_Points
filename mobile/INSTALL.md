# Versions Android & iOS (application web installable)

L'application mobile est une **PWA** : elle s'utilise dans le navigateur du
téléphone, puis s'installe sur l'écran d'accueil comme une vraie application.
Elle embarque l'OCR (tesseract.js) et le calcul des points — aucune
installation sur le téléphone, aucun store requis.

## 1. Mettre l'application en ligne (une fois, depuis GitHub)

Dans le dépôt `Calcul-Nombre_Points` sur github.com :

1. **Settings** → **Pages**
2. **Source / Build and deployment** → *Deploy from a branch*
3. Branche : la branche contenant le dossier `mobile/` (ex. `main`),
   dossier : **`/ (root)`** — ou `/docs` si le dossier a été déplacé —
   puis **Save**.
4. L'application est servie à l'adresse suivante lorsque le dossier `mobile/`
   est à la racine :
   `https://ammarbendjama.github.io/Calcul-Nombre_Points/mobile/`

Astuce : si la page 404 s'affiche, vérifiez que `mobile/index.html` est bien
présent à la racine de la branche publiée.

## 2. Installer sur Android (Chrome)

1. Ouvrez l'adresse de l'app dans **Chrome**.
2. Menu ⋮ → **Ajouter à l'écran d'accueil** → **Installer**.
3. L'icône 📐 apparaît sur l'écran d'accueil, en plein écran, comme une app.

## 3. Installer sur iPhone / iPad (Safari)

1. Ouvrez l'adresse de l'app dans **Safari** (obligatoire, pas Chrome).
2. Bouton **Partager** (carré avec flèche) → **Sur l'écran d'accueil** →
   **Ajouter**.

## 4. Utilisation

1. **🎥 Caméra** : ouvre la caméra en direct — gardez la page immobile
   ~2 s, la capture est automatique (ou **📸 Capturer** manuellement).
   Autres options : **📷 Nouvelle copie** (photo), ou fichier vidéo
   (une image extraite toutes les 1,5 s).
2. Les notes reconnues s'ajoutent à la copie en cours, avec le total.
3. Copie suivante : appuyez à nouveau sur **📷 Nouvelle copie** — le total
   de la copie finie est archivé dans « Copies comptées ».
4. **⬇️ Exporter CSV** : télécharge le récapitulatif (à ouvrir dans Excel).

## Notes techniques

- Le premier lancement télécharge le moteur OCR (~2 Mo) ; ensuite le
  service worker met l'app en cache (fonctionne hors ligne, sauf le
  premier chargement du moteur OCR si le réseau coupe).
- Éclairage franc régulier, feuille bien à plat et nette : la reconnaissance
  manuscrite est nettement meilleure.
