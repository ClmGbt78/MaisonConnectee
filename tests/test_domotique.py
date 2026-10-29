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

    repository.initialiser()

    lampe = repository.obtenir("lampe-salon")
    assert lampe is not None
    assert lampe["allume"] is True
    assert len(repository.lister()) == 3


def test_lister_filtre_par_piece_et_type(service):
    appareils = service.lister(piece="salon", type_appareil="lumiere")

    assert len(appareils) == 1
    assert appareils[0]["id"] == "lampe-salon"
    assert "marche_arret" in appareils[0]["capacites"]


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

