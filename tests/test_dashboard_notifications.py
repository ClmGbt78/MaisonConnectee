from fastapi.testclient import TestClient

from app.main import app
from app.core.security import get_current_user
from app.core.notifications import creer_notification, initialiser_stockage_notifications
from app.api.dashboard import initialiser_stockage_dashboard

client = TestClient(app)


def utilisateur_test():
    return {"id": 987654321, "nom": "Utilisateur test", "email": "tableau-test@example.com", "role": "admin", "actif": 1}


def test_preferences_dashboard_sont_persistantes():
    initialiser_stockage_dashboard()
    app.dependency_overrides[get_current_user] = utilisateur_test
    try:
        initial = client.get("/api/dashboard/preferences")
        assert initial.status_code == 200
        assert initial.json()["widgets"]
        widgets = [{"id": "resume", "size": "wide"}, {"id": "notifications", "size": "compact"}]
        enregistrement = client.put("/api/dashboard/preferences", json={"widgets": widgets})
        assert enregistrement.status_code == 200
        assert enregistrement.json()["widgets"] == widgets
        relu = client.get("/api/dashboard/preferences")
        assert relu.status_code == 200
        assert relu.json()["widgets"] == widgets
        doublons = client.put("/api/dashboard/preferences", json={"widgets": [
            {"id": "resume", "size": "wide"}, {"id": "resume", "size": "compact"},
        ]})
        assert doublons.status_code == 422
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_centre_notifications_et_isolation_utilisateur():
    initialiser_stockage_notifications()
    app.dependency_overrides[get_current_user] = utilisateur_test
    try:
        notification_id = creer_notification(987654321, "Notification de test", "Événement réservé au compte de test.", "test", "info")
        liste = client.get("/api/notifications")
        assert liste.status_code == 200
        element = next(item for item in liste.json() if item["id"] == notification_id)
        assert element["titre"] == "Notification de test"
        assert element["lu_le"] is None
        lecture = client.patch(f"/api/notifications/{notification_id}/lue")
        assert lecture.status_code == 200
        liste_non_lues = client.get("/api/notifications?non_lues=true")
        assert liste_non_lues.status_code == 200
        assert all(item["id"] != notification_id for item in liste_non_lues.json())
        suppression = client.delete(f"/api/notifications/{notification_id}")
        assert suppression.status_code == 204
    finally:
        app.dependency_overrides.pop(get_current_user, None)
