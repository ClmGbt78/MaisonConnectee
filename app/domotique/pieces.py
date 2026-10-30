import re
import sqlite3
from pathlib import Path

from app.domotique.repository import DB_PATH


class PiecesRepository:
    """Gestion persistante des pièces, sans modifier les appareils existants."""

    def __init__(self, db_path: Path | str = DB_PATH):
        self.db_path = str(db_path)

    def initialiser(self) -> None:
        with sqlite3.connect(self.db_path) as connexion:
            connexion.execute("""
                CREATE TABLE IF NOT EXISTS pieces_domotiques (
                    id TEXT PRIMARY KEY,
                    nom TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    description TEXT NOT NULL DEFAULT '',
                    couleur TEXT NOT NULL DEFAULT '#365B78'
                )
            """)
            pieces_existantes = connexion.execute(
                "SELECT DISTINCT piece FROM appareils_domotiques WHERE TRIM(piece) <> ''"
            ).fetchall()
            for (nom,) in pieces_existantes:
                identifiant = self._identifiant(nom)
                connexion.execute(
                    """INSERT OR IGNORE INTO pieces_domotiques (id, nom)
                       VALUES (?, ?)""",
                    (identifiant, nom.strip()),
                )

    @staticmethod
    def _identifiant(nom: str) -> str:
        valeur = re.sub(r"[^a-z0-9]+", "-", nom.lower()).strip("-")
        return valeur or "piece"

    def lister(self) -> list[dict]:
        with sqlite3.connect(self.db_path) as connexion:
            connexion.row_factory = sqlite3.Row
            lignes = connexion.execute("""
                SELECT p.id, p.nom, p.description, p.couleur,
                       COUNT(a.id) AS nombre_appareils
                FROM pieces_domotiques p
                LEFT JOIN appareils_domotiques a ON a.piece = p.nom COLLATE NOCASE
                GROUP BY p.id, p.nom, p.description, p.couleur
                ORDER BY p.nom COLLATE NOCASE
            """).fetchall()
        return [dict(ligne) for ligne in lignes]

    def obtenir(self, piece_id: str) -> dict | None:
        with sqlite3.connect(self.db_path) as connexion:
            connexion.row_factory = sqlite3.Row
            ligne = connexion.execute("""
                SELECT p.id, p.nom, p.description, p.couleur,
                       COUNT(a.id) AS nombre_appareils
                FROM pieces_domotiques p
                LEFT JOIN appareils_domotiques a ON a.piece = p.nom COLLATE NOCASE
                WHERE p.id = ?
                GROUP BY p.id, p.nom, p.description, p.couleur
            """, (piece_id,)).fetchone()
        return dict(ligne) if ligne else None

    def ajouter(self, nom: str, description: str, couleur: str) -> dict:
        identifiant = self._identifiant(nom)
        with sqlite3.connect(self.db_path) as connexion:
            connexion.execute(
                "INSERT INTO pieces_domotiques (id, nom, description, couleur) VALUES (?, ?, ?, ?)",
                (identifiant, nom, description, couleur),
            )
        return self.obtenir(identifiant)  # type: ignore[return-value]

    def modifier(self, piece_id: str, nom: str, description: str, couleur: str) -> dict | None:
        with sqlite3.connect(self.db_path) as connexion:
            connexion.execute("BEGIN")
            ancienne = connexion.execute(
                "SELECT nom FROM pieces_domotiques WHERE id = ?", (piece_id,)
            ).fetchone()
            if ancienne is None:
                return None
            ancien_nom = ancienne[0]
            curseur = connexion.execute(
                """UPDATE pieces_domotiques
                   SET nom = ?, description = ?, couleur = ?
                   WHERE id = ?""",
                (nom, description, couleur, piece_id),
            )
            if curseur.rowcount == 0:
                return None
            if ancien_nom != nom:
                connexion.execute(
                    "UPDATE appareils_domotiques SET piece = ? WHERE piece = ? COLLATE NOCASE",
                    (nom, ancien_nom),
                )
                for table in ("automatisations", "automatisations_conditionnelles", "extinctions_differees"):
                    existe = connexion.execute(
                        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
                    ).fetchone()
                    if existe:
                        connexion.execute(
                            f"UPDATE {table} SET piece = ? WHERE piece = ? COLLATE NOCASE",
                            (nom, ancien_nom),
                        )
        return self.obtenir(piece_id)

    def supprimer(self, piece_id: str) -> str | None:
        with sqlite3.connect(self.db_path) as connexion:
            connexion.row_factory = sqlite3.Row
            connexion.execute("BEGIN")
            piece = connexion.execute(
                "SELECT nom FROM pieces_domotiques WHERE id = ?", (piece_id,)
            ).fetchone()
            if piece is None:
                return None
            utilisee = connexion.execute(
                "SELECT 1 FROM appareils_domotiques WHERE piece = ? COLLATE NOCASE LIMIT 1",
                (piece["nom"],),
            ).fetchone()
            if utilisee:
                raise ValueError("Cette pièce contient encore des appareils. Déplace-les avant de la supprimer.")
            for table in ("automatisations", "automatisations_conditionnelles", "extinctions_differees"):
                existe = connexion.execute(
                    "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
                ).fetchone()
                if existe:
                    reference = connexion.execute(
                        f"SELECT 1 FROM {table} WHERE piece = ? COLLATE NOCASE LIMIT 1",
                        (piece["nom"],),
                    ).fetchone()
                    if reference:
                        raise ValueError("Cette pièce est encore utilisée par une automatisation.")
            connexion.execute("DELETE FROM pieces_domotiques WHERE id = ?", (piece_id,))
            return piece["nom"]
