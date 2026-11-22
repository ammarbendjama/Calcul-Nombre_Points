"""Détection des zones d'écriture (notes manuscrites) sur une page."""

from __future__ import annotations

import cv2
import numpy as np


def trouver_zones_notes(image, aire_min: float = 0.0002, aire_max: float = 0.05) -> list[tuple[int, int, int, int]]:
    """Repère les groupes d'encre plausibles (candidats notes manuscrites).

    Retourne des boîtes (x, y, largeur, hauteur) triées de haut en bas.
    Les aires sont des fractions de la surface totale de la page.
    """
    hauteur, largeur = image.shape[:2]
    surface = hauteur * largeur
    gris = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    luminosite = float(gris.mean())
    if luminosite < 110:
        gris = cv2.normalize(gris, None, 0, 255, cv2.NORM_MINMAX)

    _, binaire = cv2.threshold(gris, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    noyau = cv2.getStructuringElement(cv2.MORPH_RECT, (max(3, largeur // 200), 5))
    joint = cv2.morphologyEx(binaire, cv2.MORPH_CLOSE, noyau)

    contours, _ = cv2.findContours(joint, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    zones: list[tuple[int, int, int, int]] = []
    for contour in contours:
        x, y, l, h = cv2.boundingRect(contour)
        aire = l * h
        if aire < aire_min * surface or aire > aire_max * surface:
            continue
        if h > hauteur * 0.25:
            continue
        remplissage = cv2.contourArea(contour) / max(1.0, aire)
        if remplissage < 0.02:
            continue
        zones.append((x, y, l, h))

    return _fusionner(zones, largeur)


def _fusionner(zones: list[tuple[int, int, int, int]], largeur: int) -> list[tuple[int, int, int, int]]:
    """Réunit les zones d'une même ligne de texte (ex. "1,5" "/" "2")."""
    ecart_max = max(12, int(largeur * 0.25))
    fusionFaite = True
    while fusionFaite:
        fusionFaite = False
        restantes = zones
        zones = []
        while restantes:
            x, y, l, h = restantes.pop()
            for i, (x2, y2, l2, h2) in enumerate(zones):
                chevauch = max(0, min(y + h, y2 + h2) - max(y, y2))
                if chevauch < 0.4 * min(h, h2):
                    continue
                ecart = max(x - (x2 + l2), x2 - (x + l))
                if ecart > ecart_max:
                    continue
                nx, ny = min(x, x2), min(y, y2)
                xl, yb = max(x + l, x2 + l2), max(y + h, y2 + h2)
                zones[i] = (nx, ny, xl - nx, yb - ny)
                fusionFaite = True
                break
            else:
                zones.append((x, y, l, h))
    return sorted(zones, key=lambda z: (z[1], z[0]))


def preparer_ocr(image, zone: tuple[int, int, int, int], marge_px: int = 8):
    """Découpe une zone et la normalise pour l'OCR :
    grossissement x3, encre noire sur fond blanc, marge blanche autour.
    """
    morceau = rogner(image, zone, marge_px=marge_px)
    if morceau is None or morceau.size == 0:
        return None
    gris = cv2.cvtColor(morceau, cv2.COLOR_BGR2GRAY)
    if gris.mean() < 110:
        gris = cv2.normalize(gris, None, 0, 255, cv2.NORM_MINMAX)
    _, encre = cv2.threshold(gris, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    propre = np.where(encre > 0, 0, 255).astype(np.uint8)
    propre = cv2.resize(propre, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    return cv2.copyMakeBorder(propre, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=255)


def rogner(image, zone: tuple[int, int, int, int], marge_px: int = 8):
    """Découpe une zone avec une petite marge pour aider l'OCR."""
    h, w = image.shape[:2]
    x, y, l, hh = zone
    x0 = max(0, x - marge_px)
    y0 = max(0, y - marge_px)
    x1 = min(w, x + l + marge_px)
    y1 = min(h, y + hh + marge_px)
    return image[y0:y1, x0:x1]
