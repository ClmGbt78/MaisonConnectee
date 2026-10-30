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
            connexion.execute("""
                CREATE TABLE IF NOT EXISTS ouvertures_pieces_3d (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    piece_id TEXT NOT NULL,
                    type TEXT NOT NULL CHECK (type IN ('porte', 'fenetre')),
                    mur TEXT NOT NULL CHECK (mur IN ('nord', 'sud', 'est', 'ouest')),
                    position REAL NOT NULL DEFAULT 0,
                    largeur REAL NOT NULL,
                    hauteur REAL NOT NULL,
                    hauteur_appui REAL NOT NULL DEFAULT 0,
                    FOREIGN KEY (piece_id) REFERENCES pieces_domotiques(id) ON DELETE CASCADE
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
            resultat.append({**piece, **geometrie, "ouvertures": self._lister_ouvertures(piece["id"])})
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
    def _lister_ouvertures(self, piece_id: str) -> list[dict]:
        with sqlite3.connect(self.db_path) as connexion:
            connexion.row_factory = sqlite3.Row
            lignes = connexion.execute(
                "SELECT * FROM ouvertures_pieces_3d WHERE piece_id = ? ORDER BY id",
                (piece_id,),
            ).fetchall()
        return [dict(ligne) for ligne in lignes]

    def ajouter_ouverture(self, piece_id: str, donnees: dict) -> dict | None:
        piece = next((item for item in self.lister() if item["id"] == piece_id), None)
        if piece is None:
            return None
        self._valider_ouverture(piece, donnees)
        with sqlite3.connect(self.db_path) as connexion:
            curseur = connexion.execute("""
                INSERT INTO ouvertures_pieces_3d
                    (piece_id, type, mur, position, largeur, hauteur, hauteur_appui)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                piece_id, donnees["type"], donnees["mur"], donnees["position"],
                donnees["largeur"], donnees["hauteur"], donnees["hauteur_appui"],
            ))
            ouverture_id = curseur.lastrowid
        return next(item for item in self._lister_ouvertures(piece_id) if item["id"] == ouverture_id)

    def modifier_ouverture(self, piece_id: str, ouverture_id: int, donnees: dict) -> dict | None:
        piece = next((item for item in self.lister() if item["id"] == piece_id), None)
        if piece is None:
            return None
        self._valider_ouverture(piece, donnees)
        with sqlite3.connect(self.db_path) as connexion:
            curseur = connexion.execute("""
                UPDATE ouvertures_pieces_3d
                SET type = ?, mur = ?, position = ?, largeur = ?, hauteur = ?, hauteur_appui = ?
                WHERE id = ? AND piece_id = ?
            """, (
                donnees["type"], donnees["mur"], donnees["position"], donnees["largeur"],
                donnees["hauteur"], donnees["hauteur_appui"], ouverture_id, piece_id,
            ))
            if curseur.rowcount == 0:
                return None
        return next(item for item in self._lister_ouvertures(piece_id) if item["id"] == ouverture_id)

    def supprimer_ouverture(self, piece_id: str, ouverture_id: int) -> bool:
        with sqlite3.connect(self.db_path) as connexion:
            curseur = connexion.execute(
                "DELETE FROM ouvertures_pieces_3d WHERE id = ? AND piece_id = ?",
                (ouverture_id, piece_id),
            )
        return curseur.rowcount > 0

    @staticmethod
    def _valider_ouverture(piece: dict, ouverture: dict) -> None:
        longueur_mur = piece["largeur"] if ouverture["mur"] in ("nord", "sud") else piece["profondeur"]
        if ouverture["largeur"] > longueur_mur - 0.2:
            raise ValueError("L'ouverture est trop large pour ce mur.")
        if abs(ouverture["position"]) + ouverture["largeur"] / 2 > longueur_mur / 2 - 0.05:
            raise ValueError("La position de l'ouverture dépasse les limites du mur.")
        if ouverture["hauteur_appui"] + ouverture["hauteur"] > piece["hauteur"]:
            raise ValueError("L'ouverture dépasse la hauteur du mur.")
        if ouverture["type"] == "porte" and ouverture["hauteur_appui"] != 0:
            raise ValueError("Une porte doit commencer au niveau du sol.")

