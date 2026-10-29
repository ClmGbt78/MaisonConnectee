import pytest

from app.domotique.configuration_capteurs import ConfigurationCapteursRepository


def test_configuration_capteur_serie_est_persistante(tmp_path):
    repository = ConfigurationCapteursRepository(tmp_path / "test.db")
    repository.initialiser()

    configuration = repository.enregistrer("capteur-salon", "COM4", 9600)

    assert configuration == {
        "capteur_id": "capteur-salon",
        "port": "COM4",
        "debit": 9600,
        "protocole": "a_configurer",
    }
    assert repository.lister() == [configuration]


def test_un_port_ne_peut_pas_etre_associe_a_deux_capteurs(tmp_path):
    repository = ConfigurationCapteursRepository(tmp_path / "test.db")
    repository.initialiser()
    repository.enregistrer("capteur-a", "COM4", 9600)

    with pytest.raises(Exception):
        repository.enregistrer("capteur-b", "COM4", 9600)


def test_supprimer_configuration_ne_supprime_pas_le_capteur(tmp_path):
    repository = ConfigurationCapteursRepository(tmp_path / "test.db")
    repository.initialiser()
    repository.enregistrer("capteur-salon", "COM4", 9600)

    assert repository.supprimer("capteur-salon") is True
    assert repository.supprimer("capteur-salon") is False
    assert repository.lister() == []
