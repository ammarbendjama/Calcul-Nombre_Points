"""Synthèse des points par copie et exports CSV / JSON."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path

from .recognizer import NoteLue


@dataclass
class Zone:
    page: int
    index_image: int
    boite: tuple[int, int, int, int] | None
    note: NoteLue
    apercu: str | None = None


@dataclass
class Copie:
    numero: int
    zones: list[Zone] = field(default_factory=list)
    apercus: list[str] = field(default_factory=list)

    @property
    def total(self) -> float:
        return round(sum(z.note.points for z in self.zones), 2)

    @property
    def bareme_total(self) -> float | None:
        baremes = [z.note.bareme for z in self.zones if z.note.bareme is not None]
        return round(sum(baremes), 2) if baremes else None


def exporter_csv(copies: list[Copie], chemin: Path) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with chemin.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["copie", "page", "question/zone", "points", "bareme", "texte_lu"])
        for copie in copies:
            for i, zone in enumerate(copie.zones, start=1):
                writer.writerow(
                    [
                        copie.numero,
                        zone.page,
                        i,
                        f"{zone.note.points:g}".replace(".", ","),
                        f"{zone.note.bareme:g}".replace(".", ",") if zone.note.bareme is not None else "",
                        zone.note.brut,
                    ]
                )
            writer.writerow([copie.numero, "", "TOTAL", f"{copie.total:g}".replace(".", ","),
                             f"{copie.bareme_total:g}".replace(".", ",") if copie.bareme_total is not None else "", ""])


def exporter_json(copies: list[Copie], chemin: Path) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "copies": [
            {
                "numero": c.numero,
                "total_points": c.total,
                "bareme_total": c.bareme_total,
                "zones": [
                    {
                        "page": z.page,
                        "image_video": z.index_image,
                        "boite": list(z.boite) if z.boite else None,
                        "points": z.note.points,
                        "bareme": z.note.bareme,
                        "texte_lu": z.note.brut,
                        "confiance": z.note.confiance,
                    }
                    for z in c.zones
                ],
            }
            for c in copies
        ]
    }
    chemin.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
