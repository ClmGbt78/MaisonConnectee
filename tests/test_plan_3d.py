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


def test_ajouter_modifier_et_supprimer_une_ouverture(plan):
    piece = plan.lister()[0]
    ouverture = plan.ajouter_ouverture(piece["id"], {
        "type": "fenetre", "mur": "nord", "position": 0,
        "largeur": 1.2, "hauteur": 1.1, "hauteur_appui": 0.9,
    })
    assert ouverture["type"] == "fenetre"
    assert plan.lister()[0]["ouvertures"][0]["id"] == ouverture["id"]

    modifiee = plan.modifier_ouverture(piece["id"], ouverture["id"], {
        "type": "porte", "mur": "est", "position": 0.2,
        "largeur": 0.9, "hauteur": 2.1, "hauteur_appui": 0,
    })
    assert modifiee["type"] == "porte"
    assert modifiee["mur"] == "est"
    assert plan.supprimer_ouverture(piece["id"], ouverture["id"])
    assert plan.lister()[0]["ouvertures"] == []


def test_ouverture_hors_des_limites_du_mur_refusee(plan):
    piece = plan.lister()[0]
    with pytest.raises(ValueError, match="trop large"):
        plan.ajouter_ouverture(piece["id"], {
            "type": "porte", "mur": "nord", "position": 0,
            "largeur": 10, "hauteur": 2.1, "hauteur_appui": 0,
        })


def test_porte_avec_appui_refusee(plan):
    piece = plan.lister()[0]
    with pytest.raises(ValueError, match="niveau du sol"):
        plan.ajouter_ouverture(piece["id"], {
            "type": "porte", "mur": "nord", "position": 0,
            "largeur": 0.9, "hauteur": 2.1, "hauteur_appui": 0.2,
        })


def test_anciennes_ouvertures_recoivent_des_valeurs_par_defaut(plan):
    piece = plan.lister()[0]
    ouverture = plan.ajouter_ouverture(piece["id"], {
        "type": "porte", "mur": "nord", "position": 0,
        "largeur": 0.9, "hauteur": 2.1, "hauteur_appui": 0,
    })
    assert ouverture["sens_ouverture"] == "gauche"
    assert ouverture["angle_ouverture"] == 90


def test_configuration_sens_et_angle_porte_persiste(plan):
    piece = plan.lister()[0]
    ouverture = plan.ajouter_ouverture(piece["id"], {
        "type": "porte", "mur": "nord", "position": 0,
        "largeur": 0.9, "hauteur": 2.1, "hauteur_appui": 0,
        "sens_ouverture": "droite", "angle_ouverture": 120,
    })
    assert ouverture["sens_ouverture"] == "droite"
    assert ouverture["angle_ouverture"] == 120
    rechargee = plan.lister()[0]["ouvertures"][0]
    assert rechargee["sens_ouverture"] == "droite"
    assert rechargee["angle_ouverture"] == 120
