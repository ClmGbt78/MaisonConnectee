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
