from datetime import datetime, timedelta

from app.domotique.automations import AutomatisationRepository, MoteurAutomatisations
from app.domotique.repository import AppareilRepository


class ServiceDomotiqueFactice:
    def __init__(self):
        self.scenes = []
        self.commandes = []
        self.appareils = [{"id": "lampe-salon"}]

    def appliquer_scene(self, scene_id, piece=None):
        self.scenes.append((scene_id, piece))
        return []

    def lister(self, piece=None, type_appareil=None):
        return self.appareils

    def commander(self, appareil_id, allume):
        self.commandes.append((appareil_id, allume))


def preparer(tmp_path):
    chemin = tmp_path / "conditions.db"
    appareils = AppareilRepository(chemin)
    appareils.initialiser()
    repository = AutomatisationRepository(chemin)
    repository.initialiser()
    service = ServiceDomotiqueFactice()
    return repository, service, MoteurAutomatisations(repository, service)


def test_regle_luminosite_declenche_scene_sous_le_seuil(tmp_path):
    repository, service, moteur = preparer(tmp_path)
    maintenant = datetime(2026, 10, 29, 20, 0)
    repository.enregistrer_mesure("capteur-luminosite-salon", "luminosite", 15, maintenant)
    regle = repository.ajouter_conditionnelle({
        "nom": "Tombée de la nuit", "capteur_id": "capteur-luminosite-salon",
        "condition": "luminosite_inferieure", "seuil": 25,
        "scene_id": "lecture", "piece": "Salon",
    })

    moteur.executer_conditions(maintenant)

    assert service.scenes == [("lecture", "Salon")]
    assert repository.obtenir_conditionnelle(regle["id"])["derniere_execution"] == maintenant.isoformat()


def test_presence_declenche_scene_mais_respecte_temps_de_rearmement(tmp_path):
    repository, service, moteur = preparer(tmp_path)
    maintenant = datetime(2026, 10, 29, 20, 0)
    repository.enregistrer_mesure("detecteur-presence-salon", "presence", 1, maintenant)
    repository.ajouter_conditionnelle({
        "nom": "Accueil", "capteur_id": "detecteur-presence-salon",
        "condition": "presence_detectee", "scene_id": "accueil", "piece": "Salon",
    })

    moteur.executer_conditions(maintenant)
    moteur.executer_conditions(maintenant + timedelta(minutes=6))
    assert service.scenes == [("accueil", "Salon")]

    repository.enregistrer_mesure("detecteur-presence-salon", "presence", 0, maintenant + timedelta(minutes=7))
    moteur.executer_conditions(maintenant + timedelta(minutes=7))
    repository.enregistrer_mesure("detecteur-presence-salon", "presence", 1, maintenant + timedelta(minutes=8))
    moteur.executer_conditions(maintenant + timedelta(minutes=8))

    assert service.scenes == [("accueil", "Salon"), ("accueil", "Salon")]


def test_absence_prolongee_eteint_apres_delai(tmp_path):
    repository, service, moteur = preparer(tmp_path)
    debut_absence = datetime(2026, 10, 29, 20, 0)
    repository.enregistrer_mesure("detecteur-presence-salon", "presence", 0, debut_absence)
    repository.ajouter_conditionnelle({
        "nom": "Extinction si absent", "capteur_id": "detecteur-presence-salon",
        "condition": "absence_prolongee", "duree_absence": 10, "piece": "Salon",
    })

    moteur.executer_conditions(debut_absence + timedelta(minutes=9))
    assert service.commandes == []
    moteur.executer_conditions(debut_absence + timedelta(minutes=10))

    assert service.commandes == [("lampe-salon", False)]


def test_mesure_capteur_est_persistante(tmp_path):
    repository, _, _ = preparer(tmp_path)
    date = datetime(2026, 10, 29, 12, 0)
    repository.enregistrer_mesure("detecteur-presence-salon", "presence", 1, date)

    assert repository.mesure("detecteur-presence-salon") == {
        "appareil_id": "detecteur-presence-salon",
        "type_mesure": "presence",
        "valeur": 1,
        "mise_a_jour": date.isoformat(timespec="seconds"),
    }
