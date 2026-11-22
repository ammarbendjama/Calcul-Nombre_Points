"""Détection des zones d'écriture (notes manuscrites) sur une page."""

from __future__ import annotations

import cv2
import numpy as np


def _gris_illumination_normale(image) -> np.ndarray:
    """Gris + correction d'illumination (gomme les ombres et éclairages inégaux)."""
    gris = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    grande = max(31, (min(gris.shape[:2]) // 20) | 1)
    fond = cv2.morphologyEx(gris, cv2.MORPH_CLOSE,
                            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (grande, grande)))
    return cv2.divide(gris, fond, scale=255)


def trouver_zones_notes(image, aire_min: float = 0.0002, aire_max: float = 0.08) -> list[tuple[int, int, int, int]]:
    """Repère les groupes d'encre plausibles (candidats notes manuscrites).

    Retourne des boîtes (x, y, largeur, hauteur) triées de haut en bas.
    Les aires sont des fractions de la surface totale de la page.
    """
    hauteur, largeur = image.shape[:2]
    surface = hauteur * largeur
    gris = _gris_illumination_normale(image)

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
        if remplissage < 0.01:
            continue
        zones.append((x, y, l, h))

    return _fusionner(zones, largeur)


def _fusionner(zones: list[tuple[int, int, int, int]], largeur: int) -> list[tuple[int, int, int, int]]:
    """Réunit les zones d'une même ligne de texte (ex. "1,5" "/" "2")."""
    ecart_max = max(12, int(largeur * 0.25))
    fusion_faite = True
    while fusion_faite:
        fusion_faite = False
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
                fusion_faite = True
                break
            else:
                zones.append((x, y, l, h))
    return sorted(zones, key=lambda z: (z[1], z[0]))


def preparer_ocr(image, zone: tuple[int, int, int, int] | None, marge_px: int = 8):
    """Découpe une zone (ou prend toute la page si zone est None) et la normalise
    pour l'OCR : encre noire sur fond blanc, grossissement x3, marge blanche.
    """
    morceau = image if zone is None else rogner(image, zone, marge_px=marge_px)
    if morceau is None or morceau.size == 0:
        return None
    gris = _gris_illumination_normale(morceau)
    _, encre = cv2.threshold(gris, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    propre = np.where(encre > 0, 0, 255).astype(np.uint8)
    if zone is not None:
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
