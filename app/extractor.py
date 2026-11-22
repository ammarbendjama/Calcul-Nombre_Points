"""Extraction des pages (images uniques) à partir d'une vidéo ou de la caméra.

Principes communs à la vidéo et à la caméra en direct :
  - une image sur `pas_echantillon` est examinée ;
  - une page sombre (l'examinateur écarte la copie) marque le début d'une
    NOUVELLE copie pour la prochaine page ;
  - une transition moyenne (page tournée) marque une nouvelle page ;
  - une page claire n'est gardée que si elle diffère de la précédente.
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


def extraire_pages(obtenir_image, pas_echantillon: int, seuil_similarite: float,
                   seuil_sombre: int, seuil_clair: int, sur_frame=None):
    """Génère (image, nouvelle_copie) pour chaque page unique.

    `obtenir_image()` doit retourner l'image suivante ou None si plus rien.
    `sur_frame(image)` est appelé pour chaque image reçue (aperçu en direct).
    """
    precedent: np.ndarray | None = None
    sombre_vu = False
    page_tournee = False
    sous_seuil = 0
    index = 0
    while True:
        image = obtenir_image()
        if image is None:
            return
        if sur_frame is not None:
            sur_frame(image)
        if index % max(1, pas_echantillon) == 0:
            luminosite = float(image.mean())
            if luminosite < seuil_sombre:
                sombre_vu = True
            elif luminosite < seuil_clair:
                page_tournee = True
            else:
                petit = apercu(image)
                if precedent is None or page_tournee or sombre_vu:
                    yield image, sombre_vu
                    sous_seuil = 0
                elif similarite(precedent, petit) < seuil_similarite:
                    sous_seuil += 1
                    if sous_seuil >= 2:
                        yield image, False
                        sous_seuil = 0
                else:
                    sous_seuil = 0
                precedent = petit
                sombre_vu = False
                page_tournee = False
        index += 1


def iterer_pages(video_path, pas_echantillon: int = 5, seuil_similarite: float = 0.97,
                 seuil_sombre: int = 80, seuil_clair: int = 210):
    """Génère (index_image, image, nouvelle_copie) pour une vidéo."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Impossible d'ouvrir la vidéo : {video_path}")

    def suivant():
        ok, image = cap.read()
        return image if ok else None

    index = 0
    try:
        for image, nouvelle in extraire_pages(
            suivant, pas_echantillon, seuil_similarite, seuil_sombre, seuil_clair
        ):
            yield index, image, nouvelle
            index += 1
    finally:
        cap.release()


def iterer_pages_camera(source=0, pas_echantillon: int = 3, seuil_similarite: float = 0.97,
                        seuil_sombre: int = 80, seuil_clair: int = 210, stop_event=None,
                        sur_frame=None):
    """Génère (image, nouvelle_copie) depuis la caméra (source 0 = caméra par défaut).

    `sur_frame(image)` est appelé pour chaque image (aperçu en direct).
    Analyse arrêtée proprement quand `stop_event` est activé.
    Retourne (capture, générateur) : fermer `capture` après usage.
    """
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise RuntimeError("Impossible d'accéder à la caméra.")

    def suivant():
        if stop_event is not None and stop_event.is_set():
            return None
        ok, image = cap.read()
        return image if ok else None

    return cap, extraire_pages(
        suivant, pas_echantillon, seuil_similarite, seuil_sombre, seuil_clair,
        sur_frame=sur_frame,
    )


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
