import json
import sqlite3
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.security import get_current_user

router = APIRouter(prefix="/dashboard", tags=["Tableau de bord"])
DB_PATH = get_settings().accounts_db_file

WidgetId = Literal["resume", "appareils", "pieces", "automatisations", "notifications", "systeme"]
WidgetSize = Literal["compact", "wide"]
WIDGETS_PAR_DEFAUT = [
    {"id": "resume", "size": "wide"},
    {"id": "appareils", "size": "wide"},
    {"id": "pieces", "size": "compact"},
    {"id": "automatisations", "size": "compact"},
    {"id": "notifications", "size": "wide"},
]


class WidgetPreference(BaseModel):
    id: WidgetId
    size: WidgetSize = "compact"


class PreferencesTableau(BaseModel):
    widgets: list[WidgetPreference] = Field(max_length=6)


def initialiser_stockage_dashboard() -> None:
    with sqlite3.connect(DB_PATH) as connexion:
        connexion.execute("""
            CREATE TABLE IF NOT EXISTS preferences_tableau_bord (
                utilisateur_id INTEGER PRIMARY KEY,
                widgets_json TEXT NOT NULL,
                mis_a_jour TEXT NOT NULL
            )
        """)


@router.get("/preferences")
def obtenir_preferences(utilisateur: dict = Depends(get_current_user)):
    with sqlite3.connect(DB_PATH) as connexion:
        ligne = connexion.execute(
            "SELECT widgets_json FROM preferences_tableau_bord WHERE utilisateur_id = ?",
            (int(utilisateur["id"]),),
        ).fetchone()
    widgets = json.loads(ligne[0]) if ligne else WIDGETS_PAR_DEFAUT
    return {"widgets": widgets}


@router.put("/preferences")
def enregistrer_preferences(
    preferences: PreferencesTableau,
    utilisateur: dict = Depends(get_current_user),
):
    widgets = [widget.model_dump() for widget in preferences.widgets]
    identifiants = [widget["id"] for widget in widgets]
    if len(identifiants) != len(set(identifiants)):
        raise HTTPException(status_code=422, detail="Un widget ne peut apparaître qu'une seule fois.")
    widgets_json = json.dumps(widgets, ensure_ascii=False)
    with sqlite3.connect(DB_PATH) as connexion:
        connexion.execute(
            """
            INSERT INTO preferences_tableau_bord (utilisateur_id, widgets_json, mis_a_jour)
            VALUES (?, ?, ?)
            ON CONFLICT(utilisateur_id) DO UPDATE SET
                widgets_json = excluded.widgets_json,
                mis_a_jour = excluded.mis_a_jour
            """,
            (int(utilisateur["id"]), widgets_json, datetime.now(timezone.utc).isoformat()),
        )
    return {"widgets": widgets}
