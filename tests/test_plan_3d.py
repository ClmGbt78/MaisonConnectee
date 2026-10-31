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


def test_migration_ajoute_les_parametres_aux_anciennes_ouvertures(tmp_path):
    import sqlite3

    db = tmp_path / "ancienne-base.db"
    AppareilRepository(db).initialiser()
    pieces = PiecesRepository(db)
    pieces.initialiser()
    piece = pieces.lister()[0]
    with sqlite3.connect(db) as connexion:
        connexion.execute("""
            CREATE TABLE ouvertures_pieces_3d (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                piece_id TEXT NOT NULL,
                type TEXT NOT NULL CHECK (type IN ('porte', 'fenetre')),
                mur TEXT NOT NULL CHECK (mur IN ('nord', 'sud', 'est', 'ouest')),
                position REAL NOT NULL DEFAULT 0,
                largeur REAL NOT NULL,
                hauteur REAL NOT NULL,
                hauteur_appui REAL NOT NULL DEFAULT 0,
                FOREIGN KEY (piece_id) REFERENCES pieces_domotiques(id) ON DELETE CASCADE
            )
        """)
        connexion.execute("""
            INSERT INTO ouvertures_pieces_3d
                (piece_id, type, mur, position, largeur, hauteur, hauteur_appui)
            VALUES (?, 'porte', 'nord', 0, 0.9, 2.1, 0)
        """, (piece["id"],))

    repository = Plan3DRepository(db)
    repository.initialiser()
    ouverture = repository.lister()[0]["ouvertures"][0]
    assert ouverture["sens_ouverture"] == "gauche"
    assert ouverture["angle_ouverture"] == 90



def test_forme_personnalisee_est_persistante(plan):
    piece = plan.lister()[0]
    forme = [
        {"x": -2, "z": -1.5}, {"x": 2, "z": -1.5},
        {"x": 2, "z": 0.5}, {"x": 0, "z": 0.5},
        {"x": 0, "z": 1.5}, {"x": -2, "z": 1.5},
    ]
    resultat = plan.enregistrer(piece["id"], {
        "position_x": 0, "position_z": 0, "largeur": 4,
        "profondeur": 3, "hauteur": 2.7, "etage": 0, "forme": forme,
    })
    assert resultat["forme"] == forme
    assert plan.lister()[0]["forme"] == forme


def test_forme_personnalisee_refuse_les_murs_croises(plan):
    piece = plan.lister()[0]
    forme = [
        {"x": -2, "z": -1}, {"x": 2, "z": 1},
        {"x": -2, "z": 1}, {"x": 2, "z": -1},
        {"x": 0, "z": -2},
    ]
    with pytest.raises(ValueError, match="croiser"):
        plan.enregistrer(piece["id"], {
            "position_x": 0, "position_z": 0, "largeur": 4,
            "profondeur": 3, "hauteur": 2.7, "etage": 0, "forme": forme,
        })


def test_migration_ajoute_forme_aux_geometries_existantes(tmp_path):
    import sqlite3

    db = tmp_path / "ancienne-geometrie.db"
    AppareilRepository(db).initialiser()
    PiecesRepository(db).initialiser()
    with sqlite3.connect(db) as connexion:
        connexion.execute("""
            CREATE TABLE geometrie_pieces_3d (
                piece_id TEXT PRIMARY KEY, position_x REAL NOT NULL DEFAULT 0,
                position_z REAL NOT NULL DEFAULT 0, largeur REAL NOT NULL DEFAULT 4,
                profondeur REAL NOT NULL DEFAULT 3, hauteur REAL NOT NULL DEFAULT 2.7,
                etage INTEGER NOT NULL DEFAULT 0
            )
        """)
    repository = Plan3DRepository(db)
    repository.initialiser()
    piece = repository.lister()[0]
    assert piece["forme"] is None

def test_catalogue_accepte_les_nouveaux_meubles(plan):
    piece = plan.lister()[0]
    types = [
        "television", "meuble_tv", "table_basse", "chaise",
        "bureau", "table_chevet", "commode",
    ]
    for type_meuble in types:
        meuble = plan.ajouter_meuble(piece["id"], {
            "type": type_meuble,
            "position_x": 0,
            "position_z": 0,
            "largeur": 0.8,
            "profondeur": 0.6,
            "hauteur": 1.0,
            "rotation": 0,
        })
        assert meuble["type"] == type_meuble


def test_migration_catalogue_meubles_conserve_les_meubles_existants(tmp_path):
    import sqlite3

    db = tmp_path / "ancienne-base-meubles.db"
    AppareilRepository(db).initialiser()
    pieces = PiecesRepository(db)
    pieces.initialiser()
    piece = pieces.lister()[0]
    with sqlite3.connect(db) as connexion:
        connexion.execute("""
            CREATE TABLE meubles_pieces_3d (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                piece_id TEXT NOT NULL,
                type TEXT NOT NULL CHECK (type IN ('canape', 'fauteuil', 'table', 'lit', 'armoire', 'cuisine')),
                position_x REAL NOT NULL DEFAULT 0,
                position_z REAL NOT NULL DEFAULT 0,
                largeur REAL NOT NULL,
                profondeur REAL NOT NULL,
                hauteur REAL NOT NULL,
                rotation REAL NOT NULL DEFAULT 0,
                FOREIGN KEY (piece_id) REFERENCES pieces_domotiques(id) ON DELETE CASCADE
            )
        """)
        connexion.execute("""
            INSERT INTO meubles_pieces_3d
                (piece_id, type, position_x, position_z, largeur, profondeur, hauteur, rotation)
            VALUES (?, 'canape', 0.5, -0.25, 2.1, 0.9, 0.85, 90)
        """, (piece["id"],))

    repository = Plan3DRepository(db)
    repository.initialiser()
    meubles = repository.lister()[0]["meubles"]
    assert len(meubles) == 1
    assert meubles[0]["type"] == "canape"
    assert meubles[0]["position_x"] == 0.5
    assert meubles[0]["rotation"] == 90

    television = repository.ajouter_meuble(piece["id"], {
        "type": "television",
        "position_x": 0,
        "position_z": 0,
        "largeur": 1.25,
        "profondeur": 0.3,
        "hauteur": 0.9,
        "rotation": 0,
    })
    assert television["type"] == "television"

def test_importer_rez_de_chaussee_cree_les_pieces_et_est_rejouable(plan):
    pieces = plan.importer_plan_rez_de_chaussee()
    par_nom = {piece["nom"]: piece for piece in pieces}
    assert {"Cage d'escalier", "Chambre 1-2", "Salon", "Séjour", "Garage", "Cuisine"} <= set(par_nom)
    assert par_nom["Cage d'escalier"]["largeur"] == 2.8
    assert par_nom["Cage d'escalier"]["profondeur"] == 4.2
    assert par_nom["Chambre 1-2"]["largeur"] == 5.8
    assert par_nom["Chambre 1-2"]["etage"] == 0
    assert len(plan.importer_plan_rez_de_chaussee()) == len(pieces)
