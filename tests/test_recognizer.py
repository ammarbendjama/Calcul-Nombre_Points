"""Tests de l'analyse des notes manuscrites ("1,5/2", "0,5", ...)."""

import pytest

from app.recognizer import analyser_note


@pytest.mark.parametrize(
    "texte, attendu",
    [
        ("1,5/2", 1.5),
        ("1,5 / 2", 1.5),
        ("3/4", 3.0),
        ("0,5/1", 0.5),
        ("1.5/2", 1.5),
        ("2,5/3", 2.5),
        ("1,5", 1.5),
        ("0.5", 0.5),
        ("-  2,50 / 3", None),
    ],
)
def test_formes_reconnues(texte, attendu):
    note = analyser_note(texte)
    if attendu is None:
        assert note is None
    else:
        assert note is not None
        assert note.points == attendu


def test_entiers_refuses_par_defaut():
    assert analyser_note("3") is None
    assert analyser_note("12") is None


def test_entiers_acceptes_si_option():
    note = analyser_note("3", accepter_entiers=True)
    assert note is not None
    assert note.points == 3.0


@pytest.mark.parametrize("texte", ["", "abc", "/2", "2.5.5", "1/,", "abc1,5/2def"])
def test_formes_invalides(texte):
    assert analyser_note(texte) is None


def test_incoherences_rejetees():
    assert analyser_note("5/2") is None
    assert analyser_note("10/1") is None


def test_bareme_extrait():
    note = analyser_note("1,5/2")
    assert note is not None
    assert note.bareme == 2.0
    assert note.brut == "1,5/2"
