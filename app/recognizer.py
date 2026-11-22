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
    r"^[\s\-–—]*(\d{1,3}(?:[.,]\d+)?)[,\s]?\s*/\s*(\d{1,3}(?:[.,]\d+)?)[\s·.]?(?:f)?\s*$",
    re.IGNORECASE,
)
_DECIMAL = re.compile(r"^[\s\-–—]*(\d+)\s*[.,]\s*(\d+)\s*(?:/)?\s*f?\s*$", re.IGNORECASE)
_ENTIER = re.compile(r"^[\s\-–—]*(\d{1,2})\s*$")


def _vers_float(texte: str) -> float:
    return float(texte.replace(",", "."))


def _nettoie(points: float, numerator_brut: str, bareme: float) -> float:
    """Rattrape la virgule manuscrite avalée par l'OCR.

    "15/2" (7,5 "points" sur barème 2) vient presque toujours de "1,5/2" :
    si le numérateur (sans décimale, 2 chiffres ou plus) dépasse 2x le
    barème, on remet la virgule avant le dernier chiffre.
    Un seul chiffre dépassant le barème reste rejeté ("5/2" -> None).
    """
    decimal_presente = "," in numerator_brut or "." in numerator_brut
    deux_chiffres_plus = len(numerator_brut.lstrip("0")) >= 2
    if (not decimal_presente and deux_chiffres_plus
            and bareme > 0 and points > 2 * bareme and points < 10 * bareme):
        return points / 10
    return points


def analyser_note(texte: str, accepter_entiers: bool = False) -> NoteLue | None:
    """Analyse un texte OCR et extrait la note.

    Formes reconnues :
      - "1,5/2", "1,5 / 2", "1.5/2" -> 1.5 points sur barème 2
      - "0,5/1", "05/1"            -> 0.5 point sur barème 1
      - "1,5" ou "1.5"             -> 1.5 points (décimal sans barème)
      - "3"                        -> accepté seulement si accepter_entiers
      - virgule manuscrite avalée : "15/2" -> 1,5/2 (barème cohérent)
    """
    if not texte:
        return None
    propre = texte.strip().replace("\n", " ")

    m = _FRACTION.search(propre)
    if m:
        bareme = _vers_float(m.group(2))
        points = _vers_float(m.group(1))
        if m.group(1).startswith("0") and len(m.group(1)) >= 2 and "," not in m.group(1) and "." not in m.group(1):
            points = points / 10  # "05/1" manuscrit = "0,5/1"
        points = _nettoie(points, m.group(1), bareme)
        if not _coherent(points, bareme):
            return None
        return NoteLue(points=points, bareme=bareme, brut=m.group(0).strip(), confiance=0.9)

    m = _DECIMAL.search(propre)
    if m:
        points = _vers_float(f"{m.group(1)}.{m.group(2)}")
        return NoteLue(points=points, bareme=None, brut=m.group(0).strip(), confiance=0.75)

    if accepter_entiers:
        m = _ENTIER.search(propre)
        if m:
            points = _vers_float(m.group(1))
            return NoteLue(points=points, bareme=None, brut=m.group(0).strip(), confiance=0.55)

    return None


def notes_du_texte(texte: str) -> list[NoteLue]:
    """Extrait toutes les notes d'un texte de page complète (ordre de lecture)."""
    notes: list[NoteLue] = []
    motif = re.compile(r"(\d{1,3}(?:[.,]\d+)?)[,\s]?\s*/\s*(\d{1,3}(?:[.,]\d+)?)")
    for m in motif.finditer(texte):
        lu = analyser_note(m.group(0))
        if lu is not None:
            notes.append(lu)
    if notes:
        return notes
    for m in re.finditer(r"\b(\d+)[.,](\d+)\b", texte):
        notes.append(NoteLue(points=_vers_float(f"{m.group(1)}.{m.group(2)}"),
                             bareme=None, brut=m.group(0), confiance=0.6))
    return notes


def _coherent(points: float, bareme: float) -> bool:
    """Rejette les invraisemblances : barème nul ou énorme, points hors échelle."""
    if bareme <= 0 or bareme > 100:
        return False
    if points < 0 or points > 2 * bareme:
        return False
    return True
