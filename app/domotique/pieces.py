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
        """Supprime une pièce et toutes ses dépendances domotiques dans une transaction."""
        with sqlite3.connect(self.db_path) as connexion:
            connexion.row_factory = sqlite3.Row
            connexion.execute("BEGIN")
            piece = connexion.execute(
                "SELECT nom FROM pieces_domotiques WHERE id = ?", (piece_id,)
            ).fetchone()
            if piece is None:
                return None

            nom = piece["nom"]
            appareils = connexion.execute(
                "SELECT id FROM appareils_domotiques WHERE piece = ? COLLATE NOCASE",
                (nom,),
            ).fetchall()
            appareil_ids = [ligne["id"] for ligne in appareils]
            tables = {
                ligne["name"] for ligne in connexion.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }

            # Les automatisations horaires et conditionnelles liées à la pièce
            # ou à l'un de ses capteurs sont supprimées avant les appareils.
            if "automatisations" in tables:
                connexion.execute(
                    "DELETE FROM automatisations WHERE piece = ? COLLATE NOCASE", (nom,)
                )
            if "automatisations_conditionnelles" in tables:
                if appareil_ids:
                    placeholders = ",".join("?" for _ in appareil_ids)
                    connexion.execute(
                        "DELETE FROM automatisations_conditionnelles "
                        f"WHERE piece = ? COLLATE NOCASE OR capteur_id IN ({placeholders})",
                        [nom, *appareil_ids],
                    )
                else:
                    connexion.execute(
                        "DELETE FROM automatisations_conditionnelles WHERE piece = ? COLLATE NOCASE",
                        (nom,),
                    )
            if "extinctions_differees" in tables:
                connexion.execute(
                    "DELETE FROM extinctions_differees WHERE piece = ? COLLATE NOCASE", (nom,)
                )

            # Nettoie les données et configurations propres aux appareils supprimés.
            if appareil_ids:
                placeholders = ",".join("?" for _ in appareil_ids)
                for table, colonne in (
                    ("mesures_capteurs", "appareil_id"),
                    ("configurations_capteurs_serie", "capteur_id"),
                ):
                    if table in tables:
                        connexion.execute(
                            f"DELETE FROM {table} WHERE {colonne} IN ({placeholders})",
                            appareil_ids,
                        )
                connexion.execute(
                    f"DELETE FROM appareils_domotiques WHERE id IN ({placeholders})",
                    appareil_ids,
                )

            # Les données 3D de la pièce sont supprimées dans la même transaction.
            for table in (
                "geometrie_pieces_3d",
                "ouvertures_pieces_3d",
                "meubles_pieces_3d",
                "elements_installation_3d",
            ):
                if table in tables:
                    connexion.execute(f"DELETE FROM {table} WHERE piece_id = ?", (piece_id,))

            connexion.execute("DELETE FROM pieces_domotiques WHERE id = ?", (piece_id,))
            return nom
