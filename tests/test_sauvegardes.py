import sqlite3

import pytest

from app.core.backups import GestionnaireSauvegardes


def creer_base(chemin, valeur):
    with sqlite3.connect(chemin) as connexion:
        connexion.execute("CREATE TABLE donnees (valeur TEXT NOT NULL)")
        connexion.execute("INSERT INTO donnees (valeur) VALUES (?)", (valeur,))


def lire_valeur(chemin):
    with sqlite3.connect(chemin) as connexion:
        return connexion.execute("SELECT valeur FROM donnees").fetchone()[0]


@pytest.fixture
def gestionnaire(tmp_path):
    comptes = tmp_path / "comptes.db"
    domotique = tmp_path / "systeme_historique.db"
    creer_base(comptes, "compte-initial")
    creer_base(domotique, "maison-initiale")
    return GestionnaireSauvegardes(
        chemins_bases={
            "comptes.db": comptes,
            "systeme_historique.db": domotique,
        },
        dossier_sauvegardes=tmp_path / "backups",
        retention=5,
    ), comptes, domotique


def test_creer_sauvegarde_contient_les_deux_bases(gestionnaire):
    service, comptes, domotique = gestionnaire

    sauvegarde = service.creer_sauvegarde()

    assert sauvegarde["taille_totale_octets"] > 0
    assert len(service.lister_sauvegardes()) == 1
    dossier = service.dossier_sauvegardes / sauvegarde["identifiant"]
    assert lire_valeur(dossier / "comptes.db") == "compte-initial"
    assert lire_valeur(dossier / "systeme_historique.db") == "maison-initiale"


def test_restaurer_cree_une_sauvegarde_de_securite(gestionnaire):
    service, comptes, domotique = gestionnaire
    sauvegarde = service.creer_sauvegarde()

    with sqlite3.connect(comptes) as connexion:
        connexion.execute("UPDATE donnees SET valeur = 'compte-modifie'")
    with sqlite3.connect(domotique) as connexion:
        connexion.execute("UPDATE donnees SET valeur = 'maison-modifie'")

    resultat = service.restaurer(sauvegarde["identifiant"])

    assert lire_valeur(comptes) == "compte-initial"
    assert lire_valeur(domotique) == "maison-initiale"
    assert resultat["identifiant_restaure"] == sauvegarde["identifiant"]
    assert resultat["sauvegarde_securite"] != sauvegarde["identifiant"]
    assert len(service.lister_sauvegardes()) == 2


def test_refuser_un_identifiant_de_sauvegarde_invalide(gestionnaire):
    service, _, _ = gestionnaire

    with pytest.raises(ValueError, match="Identifiant"):
        service.restaurer("../comptes.db")


def test_refuser_la_sauvegarde_si_une_base_est_absente(tmp_path):
    service = GestionnaireSauvegardes(
        chemins_bases={
            "comptes.db": tmp_path / "absente.db",
            "systeme_historique.db": tmp_path / "domotique.db",
        },
        dossier_sauvegardes=tmp_path / "backups",
    )
    creer_base(tmp_path / "domotique.db", "maison")

    with pytest.raises(FileNotFoundError):
        service.creer_sauvegarde()

    assert service.lister_sauvegardes() == []

def test_restaurer_une_ancienne_sauvegarde_meme_avec_retention_courte(tmp_path):
    comptes = tmp_path / "comptes.db"
    domotique = tmp_path / "systeme_historique.db"
    creer_base(comptes, "compte-ancien")
    creer_base(domotique, "maison-ancienne")
    service = GestionnaireSauvegardes(
        chemins_bases={
            "comptes.db": comptes,
            "systeme_historique.db": domotique,
        },
        dossier_sauvegardes=tmp_path / "backups",
        retention=1,
    )
    ancienne = service.creer_sauvegarde()

    with sqlite3.connect(comptes) as connexion:
        connexion.execute("UPDATE donnees SET valeur = 'compte-recent'")
    with sqlite3.connect(domotique) as connexion:
        connexion.execute("UPDATE donnees SET valeur = 'maison-recente'")
    service.creer_sauvegarde(appliquer_retention=False)

    service.restaurer(ancienne["identifiant"])

    assert lire_valeur(comptes) == "compte-ancien"
    assert lire_valeur(domotique) == "maison-ancienne"
