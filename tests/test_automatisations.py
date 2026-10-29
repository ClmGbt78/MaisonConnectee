from datetime import datetime

from app.domotique.automations import AutomatisationRepository, MoteurAutomatisations


class ServiceDomotiqueFactice:
    def __init__(self):
        self.scenes = []
        self.extinctions = []
        self.appareils = [{"id": "lampe-test"}]

    def appliquer_scene(self, scene_id, piece=None):
        self.scenes.append((scene_id, piece))
        return []

    def lister(self, piece=None, type_appareil=None):
        self.extinctions.append(("lister", piece, type_appareil))
        return self.appareils

    def commander(self, appareil_id, allume):
        self.extinctions.append((appareil_id, allume))


def test_repository_persiste_une_automatisation(tmp_path):
    repository = AutomatisationRepository(tmp_path / "automation.db")
    repository.initialiser()
    item = repository.ajouter({
        "nom": "Ambiance du soir",
        "heure": "20:00",
        "jours": [1, 2, 3, 4, 5],
        "scene_id": "detente",
        "piece": "Salon",
        "extinction_minutes": 90,
    })

    assert repository.obtenir(item["id"]) == item
    assert repository.lister() == [item]
    assert repository.modifier_active(item["id"], False)["active"] is False
    assert repository.supprimer(item["id"]) is True
    assert repository.obtenir(item["id"]) is None


def test_moteur_declenche_une_fois_par_jour_et_respecte_la_piece(tmp_path):
    repository = AutomatisationRepository(tmp_path / "automation.db")
    repository.initialiser()
    item = repository.ajouter({
        "nom": "Soirée salon",
        "heure": "20:00",
        "jours": [1],
        "scene_id": "detente",
        "piece": "Salon",
        "extinction_minutes": None,
    })
    service = ServiceDomotiqueFactice()
    moteur = MoteurAutomatisations(repository, service)
    lundi_soir = datetime(2026, 10, 26, 20, 5)

    moteur.executer_cycle(lundi_soir)
    moteur.executer_cycle(lundi_soir)

    assert service.scenes == [("detente", "Salon")]
    assert repository.obtenir(item["id"])["derniere_execution"] == "2026-10-26"


def test_moteur_ignore_jour_non_selectionne_et_regle_desactivee(tmp_path):
    repository = AutomatisationRepository(tmp_path / "automation.db")
    repository.initialiser()
    item = repository.ajouter({
        "nom": "Semaine",
        "heure": "19:00",
        "jours": [1],
        "scene_id": "lecture",
        "piece": None,
        "extinction_minutes": None,
    })
    repository.modifier_active(item["id"], False)
    service = ServiceDomotiqueFactice()
    moteur = MoteurAutomatisations(repository, service)

    moteur.executer_cycle(datetime(2026, 10, 27, 20, 0))

    assert service.scenes == []


def test_extinction_differee_est_executee_apres_echeance(tmp_path):
    repository = AutomatisationRepository(tmp_path / "automation.db")
    repository.initialiser()
    repository.programmer_extinction("Bureau", 1)
    with __import__("sqlite3").connect(repository.db_path) as db:
        db.execute("UPDATE extinctions_differees SET echeance = ?", ("2020-01-01T00:00:00",))
    service = ServiceDomotiqueFactice()
    moteur = MoteurAutomatisations(repository, service)

    moteur.executer_cycle(datetime(2026, 10, 29, 12, 0))

    assert service.extinctions == [("lister", "Bureau", "lumiere"), ("lampe-test", False)]
    with __import__("sqlite3").connect(repository.db_path) as db:
        assert db.execute("SELECT executee FROM extinctions_differees").fetchone()[0] == 1
