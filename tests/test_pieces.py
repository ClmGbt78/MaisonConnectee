import sqlite3

import pytest

from app.domotique.automations import AutomatisationRepository
from app.domotique.pieces import PiecesRepository
from app.domotique.repository import AppareilRepository


@pytest.fixture
def pieces(tmp_path):
    db = tmp_path / "pieces-test.db"
    appareils = AppareilRepository(db)
    appareils.initialiser()
    repository = PiecesRepository(db)
    repository.initialiser()
    return repository


def test_initialisation_importe_les_pieces_existantes_sans_doublons(pieces):
    resultats = pieces.lister()
    noms = {item["nom"] for item in resultats}
    assert {"Salon", "Chambre", "Bureau"} <= noms
    pieces.initialiser()
    assert len(pieces.lister()) == len(resultats)


def test_creer_et_retrouver_piece_personnalisee(pieces):
    piece = pieces.ajouter("Salle de jeux", "Espace multimédia", "#123ABC")
    assert piece["nom"] == "Salle de jeux"
    assert piece["description"] == "Espace multimédia"
    assert piece["couleur"] == "#123ABC"
    assert piece["nombre_appareils"] == 0


def test_renommer_piece_met_a_jour_les_appareils_associes(pieces, tmp_path):
    appareils = AppareilRepository(tmp_path / "pieces-test.db")
    piece = next(item for item in pieces.lister() if item["nom"] == "Salon")
    modifiee = pieces.modifier(piece["id"], "Séjour", "Pièce de vie", "#AABBCC")
    assert modifiee["nom"] == "Séjour"
    assert appareils.obtenir("lampe-salon")["piece"] == "Séjour"
    assert appareils.obtenir("capteur-luminosite-salon")["piece"] == "Séjour"


def test_suppression_refusee_si_la_piece_contient_des_appareils(pieces):
    piece = next(item for item in pieces.lister() if item["nom"] == "Salon")
    with pytest.raises(ValueError, match="contient encore des appareils"):
        pieces.supprimer(piece["id"])


def test_renommage_met_a_jour_les_automatisations(pieces):
    automatisations = AutomatisationRepository(pieces.db_path)
    automatisations.initialiser()
    automatisations.ajouter({
        "nom": "Ambiance du soir", "heure": "20:00", "jours": [1, 2, 3, 4, 5],
        "scene_id": "scene-test", "piece": "Salon", "extinction_minutes": None,
    })
    salon = next(item for item in pieces.lister() if item["nom"] == "Salon")
    pieces.modifier(salon["id"], "Séjour", "Pièce de vie", "#AABBCC")
    assert automatisations.lister()[0]["piece"] == "Séjour"


def test_suppression_autorisee_pour_piece_vide(pieces):
    piece = pieces.ajouter("Atelier", "", "#365B78")
    assert pieces.supprimer(piece["id"]) == "Atelier"
    assert pieces.obtenir(piece["id"]) is None


def test_nom_de_piece_est_unique_sans_tenir_compte_de_la_casse(pieces):
    pieces.ajouter("Buanderie", "", "#365B78")
    with pytest.raises(sqlite3.IntegrityError):
        pieces.ajouter("buanderie", "", "#365B78")
