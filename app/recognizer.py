"""Reconnaissance et analyse des notes manuscrites (ex. "1,5/2")."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class NoteLue:
    """Une note lue : points obtenus et éventuellement le barème."""

    points: float
    bareme: float | None
    brut: str
    confiance: float = 1.0


_FRACTION = re.compile(
    r"^\s*(\d+(?:[.,]\d+)?),?\s*/\s*(\d+(?:[.,]\d+)?)\s*f?\s*$",
    re.IGNORECASE,
)
_DECIMAL = re.compile(r"^\s*(\d+)\s*[.,]\s*(\d+)\s*f?\s*$")
_ENTIER = re.compile(r"^\s*(\d+)\s*$")


def _vers_float(texte: str) -> float:
    return float(texte.replace(",", "."))


def analyser_note(texte: str, accepter_entiers: bool = False) -> NoteLue | None:
    """Analyse un texte OCR et extrait la note.

    Formes reconnues :
      - "1,5/2"  ou "1,5 / 2"  -> 1.5 points sur barème 2
      - "0.5/1"                  -> 0.5 point sur barème 1
      - "1,5" ou "1.5"           -> 1.5 points (décimal sans barème)
      - "3"                      -> accepté seulement si accepter_entiers
    """
    if not texte:
        return None
    propre = texte.strip().replace("\n", " ")

    m = _FRACTION.match(propre)
    if m:
        points = _vers_float(m.group(1))
        bareme = _vers_float(m.group(2))
        if not _coherent(points, bareme):
            return None
        return NoteLue(points=points, bareme=bareme, brut=propre, confiance=0.95)

    m = _DECIMAL.match(propre)
    if m:
        points = _vers_float(f"{m.group(1)}.{m.group(2)}")
        return NoteLue(points=points, bareme=None, brut=propre, confiance=0.75)

    if accepter_entiers:
        m = _ENTIER.match(propre)
        if m:
            points = _vers_float(m.group(1))
            return NoteLue(points=points, bareme=None, brut=propre, confiance=0.55)

    return None


def _coherent(points: float, bareme: float) -> bool:
    """Rejette les invraisemblances : points > 2x barème, barème nul ou énorme."""
    if bareme <= 0 or bareme > 100:
        return False
    if points < 0 or points > 2 * bareme:
        return False
    return True
