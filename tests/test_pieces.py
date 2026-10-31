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

def test_suppression_piece_nettoie_les_donnees_du_plan_3d(pieces):
    from app.domotique.plan_3d import Plan3DRepository

    piece = pieces.ajouter("Atelier 3D", "", "#365B78")
    plan = Plan3DRepository(pieces.db_path)
    plan.initialiser()
    plan.enregistrer(piece["id"], {
        "position_x": 0, "position_z": 0, "largeur": 4,
        "profondeur": 3, "hauteur": 2.7, "etage": 0,
    })
    with sqlite3.connect(pieces.db_path) as connexion:
        connexion.execute(
            """INSERT INTO meubles_pieces_3d
               (piece_id, type, largeur, profondeur, hauteur)
               VALUES (?, 'canape', 2, 1, 1)""",
            (piece["id"],),
        )
    assert pieces.supprimer(piece["id"]) == "Atelier 3D"
    with sqlite3.connect(pieces.db_path) as connexion:
        assert connexion.execute(
            "SELECT COUNT(*) FROM geometrie_pieces_3d WHERE piece_id = ?", (piece["id"],)
        ).fetchone()[0] == 0
        assert connexion.execute(
            "SELECT COUNT(*) FROM meubles_pieces_3d WHERE piece_id = ?", (piece["id"],)
        ).fetchone()[0] == 0

def test_suppression_piece_supprime_appareils_automatisations_et_dependances(pieces):
    from app.domotique.automations import AutomatisationRepository
    from app.domotique.configuration_capteurs import ConfigurationCapteursRepository
    from app.domotique.plan_3d import Plan3DRepository

    appareils = AppareilRepository(pieces.db_path)
    automatisations = AutomatisationRepository(pieces.db_path)
    automatisations.initialiser()
    configurations = ConfigurationCapteursRepository(pieces.db_path)
    configurations.initialiser()
    plan = Plan3DRepository(pieces.db_path)
    plan.initialiser()

    piece = pieces.ajouter("Pièce à supprimer", "", "#365B78")
    appareils.ajouter({
        "id": "capteur-piece-a-supprimer", "nom": "Capteur de test",
        "piece": piece["nom"], "type": "capteur",
    })
    appareils.ajouter({
        "id": "lampe-piece-a-supprimer", "nom": "Lampe de test",
        "piece": piece["nom"], "type": "lumiere",
    })
    automatisations.ajouter({
        "nom": "Horaire de la pièce", "heure": "20:00", "jours": [1],
        "scene_id": "scene-test", "piece": piece["nom"], "extinction_minutes": None,
    })
    automatisations.ajouter_conditionnelle({
        "nom": "Règle du capteur supprimé",
        "capteur_id": "capteur-piece-a-supprimer",
        "condition": "presence_detectee", "scene_id": "scene-test",
        "piece": "Bureau",
    })
    automatisations.programmer_extinction(piece["nom"], 30)
    automatisations.enregistrer_mesure("capteur-piece-a-supprimer", "presence", 1)
    configurations.enregistrer("capteur-piece-a-supprimer", "COM99", 9600)
    plan.enregistrer(piece["id"], {
        "position_x": 0, "position_z": 0, "largeur": 4,
        "profondeur": 3, "hauteur": 2.7, "etage": 0,
    })

    assert pieces.supprimer(piece["id"]) == piece["nom"]
    assert appareils.lister(piece=piece["nom"]) == []
    assert automatisations.lister() == []
    assert automatisations.lister_conditionnelles() == []
    assert automatisations.lister_mesures() == []
    assert configurations.lister() == []
    with sqlite3.connect(pieces.db_path) as connexion:
        assert connexion.execute("SELECT COUNT(*) FROM extinctions_differees").fetchone()[0] == 0
        assert connexion.execute("SELECT COUNT(*) FROM geometrie_pieces_3d WHERE piece_id = ?", (piece["id"],)).fetchone()[0] == 0
