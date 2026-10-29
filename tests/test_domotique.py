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
    assert lampe["temperature_couleur"] == 4000
    assert repository.obtenir("lampe-salon") is not None


def test_echec_adaptateur_ne_modifie_pas_luminosite(service):
    from app.domotique.service import ErreurAdaptateur

    class AdaptateurEnPanne:
        def appliquer_etat(self, appareil_id: str, allume: bool) -> bool:
            return allume

        def appliquer_luminosite(self, appareil_id: str, luminosite: int) -> int:
            raise RuntimeError("pilote indisponible")

    service.adaptateur = AdaptateurEnPanne()

    with pytest.raises(ErreurAdaptateur):
        service.regler_luminosite("lampe-salon", 25)

    assert service.obtenir("lampe-salon")["luminosite"] == 100


def test_valeur_luminosite_invalide_du_pilote_est_refusee(service):
    from app.domotique.service import ErreurAdaptateur

    class AdaptateurInvalide:
        def appliquer_etat(self, appareil_id: str, allume: bool) -> bool:
            return allume

        def appliquer_luminosite(self, appareil_id: str, luminosite: int) -> int:
            return 150

    service.adaptateur = AdaptateurInvalide()

    with pytest.raises(ErreurAdaptateur):
        service.regler_luminosite("lampe-salon", 25)

    assert service.obtenir("lampe-salon")["luminosite"] == 100


def test_temperature_couleur_est_persistante_et_limitee_aux_lumieres(service):
    lampe = service.regler_temperature_couleur("lampe-salon", 3000)

    assert lampe["temperature_couleur"] == 3000
    assert service.obtenir("lampe-salon")["temperature_couleur"] == 3000
    assert "temperature_couleur" in lampe["capacites"]

    with pytest.raises(CommandeNonSupportee):
        service.regler_temperature_couleur("ventilateur", 3000)


@pytest.mark.parametrize("temperature", [2699, 6501])
def test_temperature_couleur_hors_limites_refusee(service, temperature):
    with pytest.raises(ValueError):
        service.regler_temperature_couleur("lampe-salon", temperature)


def test_echec_adaptateur_ne_modifie_pas_temperature_couleur(service):
    from app.domotique.service import ErreurAdaptateur

    class AdaptateurEnPanne:
        def appliquer_etat(self, appareil_id: str, allume: bool) -> bool:
            return allume

        def appliquer_luminosite(self, appareil_id: str, luminosite: int) -> int:
            return luminosite

        def appliquer_temperature_couleur(self, appareil_id: str, temperature_couleur: int) -> int:
            raise RuntimeError("pilote indisponible")

    service.adaptateur = AdaptateurEnPanne()

    with pytest.raises(ErreurAdaptateur):
        service.regler_temperature_couleur("lampe-salon", 3000)

    assert service.obtenir("lampe-salon")["temperature_couleur"] == 4000
