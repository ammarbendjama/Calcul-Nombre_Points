"""Tests de la synthèse des points par copie et des exports."""

from pathlib import Path

from app.aggregate import Copie, Zone, exporter_csv, exporter_json
from app.recognizer import NoteLue
from app.recognizer import analyser_note
from app.extractor import grouper_copies


def _zone(page: int, boite: tuple[int, int, int, int], points: float, bareme: float | None) -> Zone:
    note = NoteLue(points=points, bareme=bareme, brut=f"{points:g}")
    return Zone(page=page, index_image=page * 10, boite=boite, note=note)


def test_total_points_par_copie():
    copie = Copie(
        numero=1,
        zones=[
            _zone(1, (10, 10, 40, 20), 1.5, 2.0),
            _zone(1, (10, 60, 40, 20), 0.5, 1.0),
            _zone(2, (12, 30, 40, 20), 3.0, 4.0),
        ],
    )
    assert copie.total == 5.0
    assert copie.bareme_total == 7.0


def test_total_sans_bareme():
    copie = Copie(numero=2, zones=[_zone(1, (0, 0, 1, 1), 2.0, None)])
    assert copie.total == 2.0
    assert copie.bareme_total is None


def test_zone_vide():
    copie = Copie(numero=3)
    assert copie.total == 0
    assert copie.bareme_total is None


def test_export_csv(tmp_path: Path):
    copie = Copie(numero=1, zones=[_zone(1, (10, 10, 40, 20), 1.5, 2.0)])
    cible = tmp_path / "report.csv"
    exporter_csv([copie], cible)
    contenu = cible.read_text(encoding="utf-8")
    assert "copie;page;question/zone;points;bareme;texte_lu" in contenu
    assert "1,5" in contenu
    assert "TOTAL;1,5" in contenu or ";TOTAL;1,5" in contenu


def test_export_json(tmp_path: Path):
    copie = Copie(numero=7, zones=[_zone(2, (1, 2, 3, 4), 0.5, 1.0)])
    cible = tmp_path / "report.json"
    exporter_json([copie], cible)
    import json

    data = json.loads(cible.read_text(encoding="utf-8"))
    assert data["copies"][0]["numero"] == 7
    assert data["copies"][0]["total_points"] == 0.5
    assert data["copies"][0]["zones"][0]["boite"] == [1, 2, 3, 4]


def test_note_via_ocr_texte():
    note = analyser_note("1,5/2")
    zone = Zone(page=1, index_image=0, boite=(0, 0, 10, 10), note=note)
    copie = Copie(numero=1, zones=[zone])
    assert copie.total == 1.5


def test_regroupement_copies():
    # drapeaux "nouvelle copie" pour les pages 0..4
    copie = grouper_copies([False, False, True, False, True])
    assert copie == [[0, 1], [2, 3], [4]]
