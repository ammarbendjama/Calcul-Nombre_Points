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

    noyau = cv2.getStructuringElement(cv2.MORPH_RECT, (max(3, largeur // 250), 3))
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

    zones.sort(key=lambda z: (z[1], z[0]))
    return zones


def rogner(image, zone: tuple[int, int, int, int], marge_px: int = 8):
    """Découpe une zone avec une petite marge pour aider l'OCR."""
    h, w = image.shape[:2]
    x, y, l, hh = zone
    x0 = max(0, x - marge_px)
    y0 = max(0, y - marge_px)
    x1 = min(w, x + l + marge_px)
    y1 = min(h, y + hh + marge_px)
    return image[y0:y1, x0:x1]
