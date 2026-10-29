import os

import pytest

# Secret factice réservé aux tests : évite d'exiger un fichier .env local
# lors de l'exécution de la suite sur une machine propre.
os.environ.setdefault("JWT_SECRET", "test-only-secret-not-for-production")

from fastapi.testclient import TestClient

from app.main import app
from app.core.security import get_current_user
from app.api import comptes as comptes_routes
from app.core.config import Settings

client = TestClient(app)


@pytest.fixture
def client_authentifie():
    app.dependency_overrides[get_current_user] = lambda: {
        "id": 1,
        "nom": "Compte test",
        "email": "compte-test@example.com",
        "role": "admin",
        "actif": 1,
    }
    yield client
    app.dependency_overrides.pop(get_current_user, None)


def test_accueil():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["projet"] == "Maison Connectée"
    assert response.json()["etat"] == "en fonctionnement"


def test_etat_systeme(client_authentifie):
    response = client_authentifie.get("/api/systeme")

    assert response.status_code == 200

    data = response.json()
    assert data["centrale"] == "PC Windows - développement"
    assert "heure_utc" in data
    assert "domotique" in data["modules"]
    assert "intelligence_artificielle" in data["modules"]
    assert "rgb" in data["modules"]


def test_route_indicateurs_api_enregistree_une_seule_fois():
    # FastAPI peut exposer des routeurs inclus de façon différée dans app.routes.
    # Le schéma OpenAPI reflète les chemins HTTP effectivement publiés.
    chemins = app.openapi()["paths"]

    assert "/api/systeme/indicateurs" in chemins
    assert "get" in chemins["/api/systeme/indicateurs"]


def test_indicateurs_systeme(client_authentifie):
    response = client_authentifie.get("/api/systeme/indicateurs")

    assert response.status_code == 200
    data = response.json()
    assert 0 <= data["cpu"]["utilisation_pct"] <= 100
    assert 0 <= data["ram"]["utilisation_pct"] <= 100
    assert 0 <= data["disque"]["utilisation_pct"] <= 100
    assert data["ram"]["totale_gb"] > 0
    assert data["disque"]["total_gb"] > 0


def test_modes_rgb_disponibles():
    response = client.get("/api/rgb/modes")

    assert response.status_code == 200
    assert set(response.json()["modes"]) == {
        "rainbow",
        "red_pulse",
        "spectrum_cycle",
        "spectrum_cycle_breathing",
    }



def test_mutations_domotique_et_rgb_refusent_les_requetes_sans_authentification():
    reponse_domotique = client.post(
        "/api/domotique/appareils",
        json={
            "id": "test-non-authentifie",
            "nom": "Appareil test",
            "piece": "Test",
            "type": "lumiere",
        },
    )
    reponse_rgb = client.post("/api/rgb/mode/rainbow")

    assert reponse_domotique.status_code == 401
    assert reponse_rgb.status_code == 401



def test_inscription_publique_desactivee_par_defaut(monkeypatch):
    monkeypatch.setattr(
        comptes_routes,
        "get_settings",
        lambda: Settings(allow_public_registration=False),
    )

    response = client.post(
        "/api/comptes/inscription",
        json={
            "nom": "Compte test",
            "email": "compte-test@example.com",
            "mot_de_passe": "mot-de-passe-test-long",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Les inscriptions publiques sont désactivées."



def test_lectures_privees_refusees_sans_authentification():
    chemins_prives = [
        "/api/systeme",
        "/api/systeme/indicateurs",
        "/api/systeme/historique",
        "/api/domotique/appareils",
        "/api/domotique/appareils/lampe-salon",
    ]

    for chemin in chemins_prives:
        response = client.get(chemin)
        assert response.status_code == 401, chemin
