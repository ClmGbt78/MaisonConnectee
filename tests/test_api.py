import os

# Secret factice réservé aux tests : évite d'exiger un fichier .env local
# lors de l'exécution de la suite sur une machine propre.
os.environ.setdefault("JWT_SECRET", "test-only-secret-not-for-production")

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_accueil():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["projet"] == "Maison Connectée"
    assert response.json()["etat"] == "en fonctionnement"


def test_etat_systeme():
    response = client.get("/api/systeme")

    assert response.status_code == 200

    data = response.json()
    assert data["centrale"] == "PC Windows - développement"
    assert "heure_utc" in data
    assert "domotique" in data["modules"]
    assert "intelligence_artificielle" in data["modules"]
    assert "rgb" in data["modules"]


def test_route_indicateurs_api_enregistree_une_seule_fois():
    routes_indicateurs = [
        route
        for route in app.routes
        if getattr(route, "path", None) == "/api/systeme/indicateurs"
        and "GET" in getattr(route, "methods", set())
    ]

    assert len(routes_indicateurs) == 1


def test_indicateurs_systeme():
    response = client.get("/api/systeme/indicateurs")

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
