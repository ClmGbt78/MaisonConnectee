import pytest

from app.domotique.pieces import PiecesRepository
from app.domotique.plan_3d import Plan3DRepository
from app.domotique.repository import AppareilRepository


@pytest.fixture
def plan(tmp_path):
    db = tmp_path / "plan-3d-test.db"
    AppareilRepository(db).initialiser()
    PiecesRepository(db).initialiser()
    repository = Plan3DRepository(db)
    repository.initialiser()
    return repository


def test_lister_propose_une_geometrie_initiale_sans_modifier_les_pieces(plan):
    pieces = plan.lister()
    assert pieces
    assert pieces[0]["largeur"] == 4.0
    assert pieces[0]["profondeur"] == 3.5
    assert pieces[0]["etage"] == 0
    assert plan.lister()[0]["id"] == pieces[0]["id"]


def test_enregistrer_et_recharger_la_geometrie(plan):
    piece = plan.lister()[0]
    resultat = plan.enregistrer(piece["id"], {
        "position_x": 2.5, "position_z": -1.5,
        "largeur": 5.2, "profondeur": 4.1,
        "hauteur": 2.9, "etage": 1,
    })
    assert resultat["position_x"] == 2.5
    assert resultat["position_z"] == -1.5
    assert resultat["largeur"] == 5.2
    assert resultat["profondeur"] == 4.1
    assert resultat["hauteur"] == 2.9
    assert resultat["etage"] == 1
    assert plan.lister()[0]["etage"] == 1


def test_piece_inexistante_non_enregistrable(plan):
    assert plan.enregistrer("piece-inconnue", {
        "position_x": 0, "position_z": 0, "largeur": 4,
        "profondeur": 3, "hauteur": 2.7, "etage": 0,
    }) is None
