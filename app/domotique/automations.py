import asyncio
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

from app.domotique.repository import DB_PATH


class AutomatisationRepository:
    """Stockage persistant des horaires et des extinctions différées."""

    def __init__(self, db_path: Path | str = DB_PATH):
        self.db_path = str(db_path)

    def initialiser(self) -> None:
        with sqlite3.connect(self.db_path) as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS automatisations (
                    id TEXT PRIMARY KEY,
                    nom TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    heure TEXT NOT NULL,
                    jours TEXT NOT NULL,
                    scene_id TEXT NOT NULL,
                    piece TEXT,
                    extinction_minutes INTEGER,
                    derniere_execution TEXT
                )
            """)
            db.execute("""
                CREATE TABLE IF NOT EXISTS extinctions_differees (
                    id TEXT PRIMARY KEY,
                    piece TEXT,
                    echeance TEXT NOT NULL,
                    executee INTEGER NOT NULL DEFAULT 0
                )
            """)

    @staticmethod
    def _convertir(row: sqlite3.Row) -> dict:
        item = dict(row)
        item["active"] = bool(item["active"])
        item["jours"] = json.loads(item["jours"])
        return item

    def lister(self) -> list[dict]:
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute(
                "SELECT * FROM automatisations ORDER BY heure, nom COLLATE NOCASE"
            ).fetchall()
        return [self._convertir(row) for row in rows]

    def obtenir(self, automation_id: str) -> dict | None:
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            row = db.execute("SELECT * FROM automatisations WHERE id = ?", (automation_id,)).fetchone()
        return self._convertir(row) if row else None

    def ajouter(self, item: dict) -> dict:
        automation_id = str(uuid4())
        with sqlite3.connect(self.db_path) as db:
            db.execute("""
                INSERT INTO automatisations
                (id, nom, active, heure, jours, scene_id, piece, extinction_minutes)
                VALUES (?, ?, 1, ?, ?, ?, ?, ?)
            """, (
                automation_id, item["nom"], item["heure"], json.dumps(item["jours"]),
                item["scene_id"], item.get("piece"), item.get("extinction_minutes"),
            ))
        return self.obtenir(automation_id)  # type: ignore[return-value]

    def modifier_active(self, automation_id: str, active: bool) -> dict | None:
        with sqlite3.connect(self.db_path) as db:
            cursor = db.execute(
                "UPDATE automatisations SET active = ? WHERE id = ?",
                (int(active), automation_id),
            )
            if cursor.rowcount == 0:
                return None
        return self.obtenir(automation_id)

    def supprimer(self, automation_id: str) -> bool:
        with sqlite3.connect(self.db_path) as db:
            cursor = db.execute("DELETE FROM automatisations WHERE id = ?", (automation_id,))
            return cursor.rowcount > 0

    def automations_a_lancer(self, maintenant: datetime) -> list[dict]:
        jour = maintenant.isoweekday()
        date_iso = maintenant.date().isoformat()
        heure = maintenant.strftime("%H:%M")
        candidates = [
            item for item in self.lister()
            if item["active"] and jour in item["jours"]
            and item["heure"] <= heure and item.get("derniere_execution") != date_iso
        ]
        return candidates

    def marquer_execution(self, automation_id: str, date_iso: str) -> None:
        with sqlite3.connect(self.db_path) as db:
            db.execute(
                "UPDATE automatisations SET derniere_execution = ? WHERE id = ?",
                (date_iso, automation_id),
            )

    def programmer_extinction(self, piece: str | None, minutes: int) -> None:
        echeance = (datetime.now() + timedelta(minutes=minutes)).isoformat(timespec="seconds")
        with sqlite3.connect(self.db_path) as db:
            db.execute(
                "INSERT INTO extinctions_differees (id, piece, echeance) VALUES (?, ?, ?)",
                (str(uuid4()), piece, echeance),
            )

    def extinctions_a_traiter(self, maintenant: datetime) -> list[dict]:
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute(
                "SELECT id, piece FROM extinctions_differees WHERE executee = 0 AND echeance <= ?",
                (maintenant.isoformat(timespec="seconds"),),
            ).fetchall()
        return [dict(row) for row in rows]

    def marquer_extinction(self, extinction_id: str) -> None:
        with sqlite3.connect(self.db_path) as db:
            db.execute(
                "UPDATE extinctions_differees SET executee = 1 WHERE id = ?",
                (extinction_id,),
            )


class MoteurAutomatisations:
    """Moteur local : vérifie les horaires périodiquement, sans service externe."""

    def __init__(self, repository: AutomatisationRepository, service_domotique):
        self.repository = repository
        self.service_domotique = service_domotique
        self._task: asyncio.Task | None = None

    async def demarrer(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._boucle())

    async def arreter(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _boucle(self) -> None:
        while True:
            try:
                self.executer_cycle()
            except Exception:
                # Une erreur ponctuelle ne doit pas arrêter les cycles suivants.
                pass
            await asyncio.sleep(15)

    def executer_cycle(self, maintenant: datetime | None = None) -> None:
        maintenant = maintenant or datetime.now()
        for item in self.repository.automations_a_lancer(maintenant):
            try:
                self.service_domotique.appliquer_scene(item["scene_id"], piece=item.get("piece"))
                if item.get("extinction_minutes"):
                    self.repository.programmer_extinction(
                        item.get("piece"), item["extinction_minutes"]
                    )
            finally:
                # Évite de relancer en boucle une règle défaillante à chaque cycle.
                self.repository.marquer_execution(item["id"], maintenant.date().isoformat())

        for extinction in self.repository.extinctions_a_traiter(maintenant):
            try:
                appareils = self.service_domotique.lister(
                    piece=extinction["piece"], type_appareil="lumiere"
                )
                for appareil in appareils:
                    self.service_domotique.commander(appareil["id"], False)
            finally:
                self.repository.marquer_extinction(extinction["id"])
