"""Génère une vidéo de démonstration : 2 copies, 2 pages chacune.

Usage : python scripts/make_demo_video.py demo.mp4
Entre les pages, l'« examinateur » écarte la feuille (transition moyenne) ;
entre les copies, la caméra s'éloigne (transition sombre) : c'est ainsi que
l'application repère les changements de copie.
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

import cv2
import numpy as np

# notes : (texte lu par l'OCR, points, barème)
PAGES = [
    # copie 1
    {"copie": 1, "page": 1, "titre": True, "notes": [("1,5/2", 1.5, 2), ("0,5/1", 0.5, 1), ("2,5/3", 2.5, 3)]},
    {"copie": 1, "page": 2, "titre": False, "notes": [("1/1", 1.0, 1), ("2/2", 1.0, 2)]},
    # copie 2
    {"copie": 2, "page": 1, "titre": True, "notes": [("3/4", 3.0, 4), ("1,5/2", 1.5, 2), ("0,5/1", 0.5, 1)]},
    {"copie": 2, "page": 2, "titre": False, "notes": [("2/3", 2.0, 3)]},
]


def page_image(info: dict) -> np.ndarray:
    image = np.full((720, 1080, 3), 245, dtype=np.uint8)
    if info["titre"]:
        cv2.putText(image, "COPIE EXAMEN", (60, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (30, 30, 30), 3)
    cv2.putText(image, f"page {info['page']}", (820, 660), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (30, 30, 30), 2)
    y = 160 if info["titre"] else 80
    for i, (texte, _p, _b) in enumerate(info["notes"], start=1):
        cv2.putText(image, f"Q{i} =", (80, y), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (30, 30, 30), 2)
        cv2.putText(image, texte, (720, y), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 200), 3)
        y += 120
    return image


def ecrire_page(entree, image: np.ndarray, secondes: int, fps: int) -> None:
    for _ in range(secondes * fps):
        dx = random.randint(-6, 6)
        dy = random.randint(-6, 6)
        matrice = np.float32([[1, 0, dx], [0, 1, dy]])
        entree.write(cv2.warpAffine(image, matrice, (image.shape[1], image.shape[0])))


def ecrire_transition(entree, secondes: int, fps: int, lumiere: int) -> None:
    for _ in range(secondes * fps):
        valeur = int(lumiere + random.uniform(-10, 10))
        entree.write(np.full((720, 1080, 3), valeur, dtype=np.uint8))


def main() -> int:
    parser = argparse.ArgumentParser(description="Génère une vidéo de démonstration.")
    parser.add_argument("sortie", nargs="?", default="demo.mp4")
    parser.add_argument("--fps", type=int, default=25)
    args = parser.parse_args()

    sortie = cv2.VideoWriter(args.sortie, cv2.VideoWriter_fourcc(*"mp4v"), args.fps, (1080, 720))
    if not sortie.isOpened():
        print("Impossible de créer la vidéo.", file=sys.stderr)
        return 1

    precedente = None
    for info in PAGES:
        if precedente is not None:
            # transition sombre (nouvelle copie) ou moyenne (page suivante)
            separation_copie = info["page"] == 1 and precedente != info["copie"]
            ecrire_transition(sortie, 2 if separation_copie else 1, args.fps,
                              50 if separation_copie else 120)
        ecrire_page(sortie, page_image(info), 3, args.fps)
        precedente = info["copie"]

    sortie.release()
    print(f"Vidéo de démonstration créée : {Path(args.sortie).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
