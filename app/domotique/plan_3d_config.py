import json
import sqlite3
from pathlib import Path

from app.domotique.repository import DB_PATH


class ConfigurationPlan3DRepository:
    """Persistance additive des finitions et scénarios déclenchés depuis le plan 3D."""

    def __init__(self, db_path: Path | str = DB_PATH):
        self.db_path = str(db_path)

    def initialiser(self) -> None:
        with sqlite3.connect(self.db_path) as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS finitions_pieces_3d (
                    piece_id TEXT PRIMARY KEY,
                    mur_interieur TEXT NOT NULL DEFAULT '{"materiau":"peinture","couleur":"#e0e7ef"}',
                    mur_exterieur TEXT NOT NULL DEFAULT '{"materiau":"enduit","couleur":"#d6d3d1"}',
                    sol TEXT NOT NULL DEFAULT '{"materiau":"carrelage","couleur":"#b8c7d8"}',
                    plafond TEXT NOT NULL DEFAULT '{"materiau":"platre","couleur":"#f1f5f9"}',
                    FOREIGN KEY (piece_id) REFERENCES pieces_domotiques(id) ON DELETE CASCADE
                )
            """)
            db.execute("""
                CREATE TABLE IF NOT EXISTS scenarios_plan_3d (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nom TEXT NOT NULL UNIQUE,
                    description TEXT NOT NULL DEFAULT '',
                    portee TEXT NOT NULL CHECK (portee IN ('maison','selection')),
                    appareils_json TEXT NOT NULL DEFAULT '[]',
                    actif INTEGER NOT NULL DEFAULT 1
                )
            """)

    def lister_finitions(self) -> list[dict]:
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute("SELECT * FROM finitions_pieces_3d ORDER BY piece_id").fetchall()
        return [{**dict(row), **{key: json.loads(row[key]) for key in ("mur_interieur", "mur_exterieur", "sol", "plafond")}} for row in rows]

    def enregistrer_finitions(self, piece_id: str, data: dict) -> dict:
        colonnes = ("mur_interieur", "mur_exterieur", "sol", "plafond")
        valeurs = [json.dumps(data[key], ensure_ascii=False) for key in colonnes]
        with sqlite3.connect(self.db_path) as db:
            db.execute("""INSERT INTO finitions_pieces_3d
                (piece_id,mur_interieur,mur_exterieur,sol,plafond) VALUES (?,?,?,?,?)
                ON CONFLICT(piece_id) DO UPDATE SET mur_interieur=excluded.mur_interieur,
                mur_exterieur=excluded.mur_exterieur,sol=excluded.sol,plafond=excluded.plafond""",
                [piece_id, *valeurs])
        return next(item for item in self.lister_finitions() if item["piece_id"] == piece_id)

    def lister_scenarios(self) -> list[dict]:
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute("SELECT * FROM scenarios_plan_3d ORDER BY nom COLLATE NOCASE").fetchall()
        return [{**dict(row), "appareils": json.loads(row["appareils_json"]), "actif": bool(row["actif"])} for row in rows]

    def ajouter_scenario(self, data: dict) -> dict:
        with sqlite3.connect(self.db_path) as db:
            cursor = db.execute("INSERT INTO scenarios_plan_3d(nom,description,portee,appareils_json) VALUES (?,?,?,?)",
                (data["nom"], data["description"], data["portee"], json.dumps(data["appareils"])))
            identifiant = cursor.lastrowid
        return next(item for item in self.lister_scenarios() if item["id"] == identifiant)

    def modifier_scenario(self, identifiant: int, data: dict) -> dict | None:
        with sqlite3.connect(self.db_path) as db:
            cursor = db.execute("UPDATE scenarios_plan_3d SET nom=?,description=?,portee=?,appareils_json=? WHERE id=?",
                (data["nom"], data["description"], data["portee"], json.dumps(data["appareils"]), identifiant))
        return next((item for item in self.lister_scenarios() if item["id"] == identifiant), None) if cursor.rowcount else None

    def supprimer_scenario(self, identifiant: int) -> bool:
        with sqlite3.connect(self.db_path) as db:
            cursor = db.execute("DELETE FROM scenarios_plan_3d WHERE id=?", (identifiant,))
        return cursor.rowcount > 0
