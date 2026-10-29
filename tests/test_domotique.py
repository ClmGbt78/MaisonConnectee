from app.domotique.adapters.simulation import AdaptateurSimulation
from app.domotique.repository import AppareilRepository
from app.domotique.service import (
    AppareilIntrouvable,
    AppareilService,
    CommandeNonSupportee,
)
import pytest


@pytest.fixture
def service(tmp_path):
    repository = AppareilRepository(tmp_path / "domotique-test.db")
    repository.initialiser()
    return AppareilService(repository, AdaptateurSimulation())


def test_initialisation_preserve_les_appareils_existants(tmp_path):
    repository = AppareilRepository(tmp_path / "domotique-test.db")
    repository.initialiser()
    repository.definir_etat("lampe-salon", True)
    repository.definir_luminosite("lampe-salon", 42)

    repository.initialiser()

    lampe = repository.obtenir("lampe-salon")
    assert lampe is not None
    assert lampe["allume"] is True
    assert lampe["luminosite"] == 42
    assert len(repository.lister()) == 3


def test_lister_filtre_par_piece_et_type(service):
    appareils = service.lister(piece="salon", type_appareil="lumiere")

    assert len(appareils) == 1
    assert appareils[0]["id"] == "lampe-salon"
    assert "marche_arret" in appareils[0]["capacites"]
    assert "luminosite" in appareils[0]["capacites"]


def test_capteur_est_en_lecture_seule(service):
    service.ajouter({
        "id": "capteur-test",
        "nom": "Capteur test",
        "piece": "Bureau",
        "type": "capteur",
    })

    capteur = service.obtenir("capteur-test")
    assert capteur["capacites"] == ["lecture"]

    with pytest.raises(CommandeNonSupportee):
        service.commander("capteur-test", True)


def test_commande_simulee_persiste_le_nouvel_etat(service):
    lampe = service.commander("lampe-salon", True)

    assert lampe["allume"] is True
    assert service.obtenir("lampe-salon")["allume"] is True


def test_appareil_absent_declenche_une_erreur_metier(service):
    with pytest.raises(AppareilIntrouvable):
        service.obtenir("appareil-inexistant")

def test_echec_adaptateur_ne_modifie_pas_etat(service):
    from app.domotique.service import ErreurAdaptateur

    class AdaptateurEnPanne:
        def appliquer_etat(self, appareil_id: str, allume: bool) -> bool:
            raise RuntimeError("pilote indisponible")

    service.adaptateur = AdaptateurEnPanne()

    with pytest.raises(ErreurAdaptateur):
        service.commander("lampe-salon", True)

    assert service.obtenir("lampe-salon")["allume"] is False



def test_luminosite_est_persistante_et_limitee_aux_lumieres(service):
    lampe = service.regler_luminosite("lampe-salon", 35)

    assert lampe["luminosite"] == 35
    assert service.obtenir("lampe-salon")["luminosite"] == 35
    assert "luminosite" in lampe["capacites"]

    with pytest.raises(CommandeNonSupportee):
        service.regler_luminosite("ventilateur", 35)


def test_luminosite_invalide_est_refusee(service):
    with pytest.raises(ValueError):
        service.regler_luminosite("lampe-salon", 101)


def test_migration_luminosite_preserve_etat_existant(tmp_path):
    import sqlite3

    chemin = tmp_path / "ancienne-base.db"
    with sqlite3.connect(chemin) as connexion:
        connexion.execute("""
            CREATE TABLE appareils_domotiques (
                id TEXT PRIMARY KEY, nom TEXT NOT NULL, piece TEXT NOT NULL,
                type TEXT NOT NULL, allume INTEGER NOT NULL DEFAULT 0
            )
        """)
        connexion.execute(
            "INSERT INTO appareils_domotiques VALUES (?, ?, ?, ?, ?)",
            ("lampe-perso", "Lampe perso", "Bureau", "lumiere", 1),
        )

    repository = AppareilRepository(chemin)
    repository.initialiser()

    lampe = repository.obtenir("lampe-perso")
    assert lampe is not None
    assert lampe["allume"] is True
    assert lampe["luminosite"] == 100
    assert repository.obtenir("lampe-salon") is not None
