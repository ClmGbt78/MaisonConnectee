import sqlite3
from pathlib import Path

from app.domotique.pieces import PiecesRepository
from app.domotique.repository import DB_PATH


class Plan3DRepository:
    """Stocke la géométrie de chaque pièce sans toucher aux données domotiques."""

    def __init__(self, db_path: Path | str = DB_PATH):
        self.db_path = str(db_path)
        self.pieces = PiecesRepository(db_path)

    def initialiser(self) -> None:
        with sqlite3.connect(self.db_path) as connexion:
            connexion.execute("""
                CREATE TABLE IF NOT EXISTS geometrie_pieces_3d (
                    piece_id TEXT PRIMARY KEY,
                    position_x REAL NOT NULL DEFAULT 0,
                    position_z REAL NOT NULL DEFAULT 0,
                    largeur REAL NOT NULL DEFAULT 4,
                    profondeur REAL NOT NULL DEFAULT 3,
                    hauteur REAL NOT NULL DEFAULT 2.7,
                    etage INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (piece_id) REFERENCES pieces_domotiques(id)
                )
            """)

    def lister(self) -> list[dict]:
        pieces = self.pieces.lister()
        with sqlite3.connect(self.db_path) as connexion:
            connexion.row_factory = sqlite3.Row
            geometries = {
                ligne["piece_id"]: dict(ligne)
                for ligne in connexion.execute(
                    "SELECT * FROM geometrie_pieces_3d"
                ).fetchall()
            }

        resultat = []
        for index, piece in enumerate(pieces):
            geometrie = geometries.get(piece["id"])
            if geometrie is None:
                geometrie = {
                    "position_x": float((index % 3) * 5 - 5),
                    "position_z": float((index // 3) * 4 - 2),
                    "largeur": 4.0,
                    "profondeur": 3.5,
                    "hauteur": 2.7,
                    "etage": 0,
                }
            resultat.append({**piece, **geometrie})
        return resultat

    def enregistrer(self, piece_id: str, donnees: dict) -> dict | None:
        if self.pieces.obtenir(piece_id) is None:
            return None
        with sqlite3.connect(self.db_path) as connexion:
            connexion.execute("""
                INSERT INTO geometrie_pieces_3d
                    (piece_id, position_x, position_z, largeur, profondeur, hauteur, etage)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(piece_id) DO UPDATE SET
                    position_x = excluded.position_x,
                    position_z = excluded.position_z,
                    largeur = excluded.largeur,
                    profondeur = excluded.profondeur,
                    hauteur = excluded.hauteur,
                    etage = excluded.etage
            """, (
                piece_id, donnees["position_x"], donnees["position_z"],
                donnees["largeur"], donnees["profondeur"],
                donnees["hauteur"], donnees["etage"],
            ))
        return next((piece for piece in self.lister() if piece["id"] == piece_id), None)
