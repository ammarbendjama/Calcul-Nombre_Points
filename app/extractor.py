"""Extraction des pages (images uniques) à partir d'une vidéo de copies.

Principes :
  - Une image sur `pas_echantillon` est examinée.
  - Une page sombre (l'examinateur écarte la copie) marque une transition.
      * transition très sombre (>seuil_sombre) -> la prochaine page commence
        une NOUVELLE copie ;
      * transition moyenne (tourner une page) -> prochaine page = nouvelle
        page de la même copie.
  - Une page claire n'est gardée que si elle diffère de la page précédente
    (l'examinateur reste plusieurs secondes sur la même page).
"""

from __future__ import annotations

import cv2
import numpy as np


def apercu(image) -> np.ndarray:
    """Version réduite et floutée pour comparer deux pages."""
    h, w = image.shape[:2]
    echelle = 320.0 / max(1, w)
    petite = cv2.resize(image, (320, max(1, int(h * echelle))))
    gris = cv2.cvtColor(petite, cv2.COLOR_BGR2GRAY)
    return cv2.GaussianBlur(gris, (21, 21), 0)


def similarite(a, b) -> float:
    """1.0 = images quasi identiques ; 0.0 = très différentes."""
    diff = cv2.absdiff(a, b)
    fraction = float(np.count_nonzero(diff > 60)) / diff.size
    return 1.0 - fraction


def iterer_pages(video_path, pas_echantillon: int = 5, seuil_similarite: float = 0.97,
                 seuil_sombre: int = 80, seuil_clair: int = 210):
    """Génère (index_image, image, nouvelle_copie) pour chaque page unique.

    `nouvelle_copie` est True si une transition sombre (changement de copie)
    a eu lieu depuis la page précédente.
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Impossible d'ouvrir la vidéo : {video_path}")

    precedent: np.ndarray | None = None
    sombre_vu = False
    page_tournee = False
    sous_seuil = 0
    try:
        index = 0
        while True:
            ok, image = cap.read()
            if not ok:
                break
            if index % max(1, pas_echantillon) == 0:
                luminosite = float(image.mean())
                if luminosite < seuil_sombre:
                    sombre_vu = True
                elif luminosite < seuil_clair:
                    page_tournee = True
                else:
                    petit = apercu(image)
                    if precedent is None or page_tournee or sombre_vu:
                        yield index, image, sombre_vu
                        sous_seuil = 0
                    elif similarite(precedent, petit) < seuil_similarite:
                        sous_seuil += 1
                        if sous_seuil >= 2:
                            yield index, image, False
                            sous_seuil = 0
                    else:
                        sous_seuil = 0
                    precedent = petit
                    sombre_vu = False
                    page_tournee = False
            index += 1
    finally:
        cap.release()


def grouper_copies(flags: list[bool]) -> list[list[int]]:
    """Regroupe les index de pages en copies à partir des drapeaux.

    `flags[i]` vaut True si la page i commence une nouvelle copie.
    """
    if not flags:
        return []
    copies: list[list[int]] = [[0]]
    for i, nouvelle in enumerate(flags[1:], start=1):
        if nouvelle:
            copies.append([i])
        else:
            copies[-1].append(i)
    return copies
