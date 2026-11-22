"""Détection de pages uniques (vidéo ou caméra directe)."""

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


class DetecteurPages:
    """Machine à états : décide quand une image est une page nouvelle/copie nouvelle.

    - image sombre (copie écartée) -> la prochaine page démarre une NOUVELLE copie ;
    - transition moyenne (page tournée) -> nouvelle page, même copie ;
    - page claire : gardée si différente de la précédente (hystérésis 2 échantillons).
    """

    def __init__(self, pas_echantillon: int = 3, seuil_similarite: float = 0.97,
                 seuil_sombre: int = 60, seuil_clair: int = 150):
        self.pas = max(1, pas_echantillon)
        self.seuil_similarite = seuil_similarite
        self.seuil_sombre = seuil_sombre
        self.seuil_clair = seuil_clair
        self.precedent: np.ndarray | None = None
        self.sombre_vu = False
        self.page_tournee = False
        self.sous_seuil = 0
        self._index = 0

    def traiter(self, image) -> tuple[str, bool] | None:
        """Retourne ("page", nouvelle_copie) si une page est capturée, sinon None."""
        self._index += 1
        if (self._index - 1) % self.pas != 0:
            return None

        luminosite = float(image.mean())
        if luminosite < self.seuil_sombre:
            self.sombre_vu = True
            return None
        if luminosite < self.seuil_clair:
            self.page_tournee = True
            return None

        petit = apercu(image)
        if self.precedent is None or self.page_tournee or self.sombre_vu:
            nouvel_evenement = ("page", self.sombre_vu)
        elif similarite(self.precedent, petit) < self.seuil_similarite:
            self.sous_seuil += 1
            if self.sous_seuil >= 2:
                self.sous_seuil = 0
                nouvel_evenement = ("page", False)
            else:
                self.precedent = petit
                self.page_tournee = False
                self.sombre_vu = False
                return None
        else:
            self.sous_seuil = 0
            self.precedent = petit
            self.page_tournee = False
            self.sombre_vu = False
            return None

        self.precedent = petit
        self.page_tournee = False
        self.sombre_vu = False
        return nouvel_evenement


def extraire_pages(obtenir_image, pas_echantillon: int, seuil_similarite: float,
                   seuil_sombre: int, seuil_clair: int, sur_frame=None):
    """Génère (image, nouvelle_copie) pour chaque page unique d'un flux d'images."""
    detecteur = DetecteurPages(pas_echantillon, seuil_similarite, seuil_sombre, seuil_clair)
    while True:
        image = obtenir_image()
        if image is None:
            return
        if sur_frame is not None:
            sur_frame(image)
        evenement = detecteur.traiter(image)
        if evenement is not None:
            yield image, evenement[1]


def iterer_pages(video_path, pas_echantillon: int = 5, seuil_similarite: float = 0.97,
                 seuil_sombre: int = 60, seuil_clair: int = 150):
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


def grouper_copies(flags: list[bool]) -> list[list[int]]:
    """Regroupe les index de pages en copies ; flags[i] = la page i commence une copie."""
    if not flags:
        return []
    copies: list[list[int]] = [[0]]
    for i, nouvelle in enumerate(flags[1:], start=1):
        if nouvelle:
            copies.append([i])
        else:
            copies[-1].append(i)
    return copies
