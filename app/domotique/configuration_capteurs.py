"""Persistance des associations capteurs logiques / ports série.

Cette configuration est descriptive : elle n'ouvre aucun port et n'active
aucun pilote physique.
"""
import sqlite3
from pathlib import Path

from app.domotique.repository import DB_PATH


class ConfigurationCapteursRepository:
    def __init__(self, db_path: Path | str = DB_PATH):
        self.db_path = str(db_path)

    def initialiser(self) -> None:
        with sqlite3.connect(self.db_path) as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS configurations_capteurs_serie (
                    capteur_id TEXT PRIMARY KEY,
                    port TEXT NOT NULL UNIQUE,
                    debit INTEGER NOT NULL DEFAULT 9600,
                    protocole TEXT NOT NULL DEFAULT 'a_configurer'
                )
            """)

    def lister(self) -> list[dict]:
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute("""
                SELECT capteur_id, port, debit, protocole
                FROM configurations_capteurs_serie ORDER BY capteur_id
            """).fetchall()
        return [dict(row) for row in rows]

    def obtenir(self, capteur_id: str) -> dict | None:
        return next((item for item in self.lister() if item["capteur_id"] == capteur_id), None)

    def enregistrer(self, capteur_id: str, port: str, debit: int) -> dict:
        with sqlite3.connect(self.db_path) as db:
            db.execute("""
                INSERT INTO configurations_capteurs_serie (capteur_id, port, debit)
                VALUES (?, ?, ?)
                ON CONFLICT(capteur_id) DO UPDATE SET
                    port = excluded.port, debit = excluded.debit
            """, (capteur_id, port, debit))
        return self.obtenir(capteur_id)  # type: ignore[return-value]

    def supprimer(self, capteur_id: str) -> bool:
        with sqlite3.connect(self.db_path) as db:
            cursor = db.execute(
                "DELETE FROM configurations_capteurs_serie WHERE capteur_id = ?",
                (capteur_id,),
            )
        return cursor.rowcount > 0
