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
                    sens_ouverture TEXT NOT NULL DEFAULT 'gauche',
                    angle_ouverture INTEGER NOT NULL DEFAULT 90,
                    FOREIGN KEY (piece_id) REFERENCES pieces_domotiques(id) ON DELETE CASCADE
                )
            """)
            connexion.execute("""
                CREATE TABLE IF NOT EXISTS meubles_pieces_3d (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    piece_id TEXT NOT NULL,
                    type TEXT NOT NULL CHECK (type IN ('canape', 'fauteuil', 'table', 'lit', 'armoire', 'cuisine')),
                    position_x REAL NOT NULL DEFAULT 0,
                    position_z REAL NOT NULL DEFAULT 0,
                    largeur REAL NOT NULL,
                    profondeur REAL NOT NULL,
                    hauteur REAL NOT NULL,
                    rotation REAL NOT NULL DEFAULT 0,
                    FOREIGN KEY (piece_id) REFERENCES pieces_domotiques(id) ON DELETE CASCADE
                )
            """)
            connexion.execute("""
                CREATE TABLE IF NOT EXISTS elements_installation_3d (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    piece_id TEXT NOT NULL,
                    type TEXT NOT NULL CHECK (type IN ('prise', 'interrupteur', 'appareil')),
                    position_x REAL NOT NULL DEFAULT 0,
                    position_z REAL NOT NULL DEFAULT 0,
                    hauteur REAL NOT NULL DEFAULT 0.3,
                    orientation TEXT NOT NULL DEFAULT 'nord',
                    circuit TEXT NOT NULL DEFAULT 'Circuit général',
                    appareil_id TEXT,
                    FOREIGN KEY (piece_id) REFERENCES pieces_domotiques(id) ON DELETE CASCADE
                )
            """)
            colonnes = {ligne[1] for ligne in connexion.execute("PRAGMA table_info(ouvertures_pieces_3d)")}
            if "sens_ouverture" not in colonnes:
                connexion.execute("ALTER TABLE ouvertures_pieces_3d ADD COLUMN sens_ouverture TEXT NOT NULL DEFAULT 'gauche'")
            if "angle_ouverture" not in colonnes:
                connexion.execute("ALTER TABLE ouvertures_pieces_3d ADD COLUMN angle_ouverture INTEGER NOT NULL DEFAULT 90")

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
            resultat.append({**piece, **geometrie, "ouvertures": self._lister_ouvertures(piece["id"]), "meubles": self._lister_meubles(piece["id"])})
        return resultat

    def enregistrer(self, piece_id: str, donnees: dict) -> dict | None:
        piece = self.pieces.obtenir(piece_id)
        if piece is None:
            return None
        piece_avec_geometrie = {**piece, **donnees}
        for ouverture in self._lister_ouvertures(piece_id):
            self._valider_ouverture(piece_avec_geometrie, ouverture)
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
    def _lister_meubles(self, piece_id: str) -> list[dict]:
        with sqlite3.connect(self.db_path) as connexion:
            connexion.row_factory = sqlite3.Row
            lignes = connexion.execute(
                "SELECT * FROM meubles_pieces_3d WHERE piece_id = ? ORDER BY id",
                (piece_id,),
            ).fetchall()
        return [dict(ligne) for ligne in lignes]

    def ajouter_meuble(self, piece_id: str, donnees: dict) -> dict | None:
        piece = next((item for item in self.lister() if item["id"] == piece_id), None)
        if piece is None:
            return None
        self._valider_meuble(piece, donnees)
        with sqlite3.connect(self.db_path) as connexion:
            curseur = connexion.execute("""
                INSERT INTO meubles_pieces_3d
                    (piece_id, type, position_x, position_z, largeur, profondeur, hauteur, rotation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (piece_id, donnees["type"], donnees["position_x"], donnees["position_z"],
                  donnees["largeur"], donnees["profondeur"], donnees["hauteur"], donnees["rotation"]))
            meuble_id = curseur.lastrowid
        return next(item for item in self._lister_meubles(piece_id) if item["id"] == meuble_id)

    def modifier_meuble(self, piece_id: str, meuble_id: int, donnees: dict) -> dict | None:
        piece = next((item for item in self.lister() if item["id"] == piece_id), None)
        if piece is None:
            return None
        self._valider_meuble(piece, donnees)
        with sqlite3.connect(self.db_path) as connexion:
            curseur = connexion.execute("""
                UPDATE meubles_pieces_3d SET type=?, position_x=?, position_z=?, largeur=?,
                    profondeur=?, hauteur=?, rotation=? WHERE id=? AND piece_id=?
            """, (donnees["type"], donnees["position_x"], donnees["position_z"], donnees["largeur"],
                  donnees["profondeur"], donnees["hauteur"], donnees["rotation"], meuble_id, piece_id))
            if curseur.rowcount == 0:
                return None
        return next(item for item in self._lister_meubles(piece_id) if item["id"] == meuble_id)

    def supprimer_meuble(self, piece_id: str, meuble_id: int) -> bool:
        with sqlite3.connect(self.db_path) as connexion:
            curseur = connexion.execute(
                "DELETE FROM meubles_pieces_3d WHERE id=? AND piece_id=?", (meuble_id, piece_id)
            )
        return curseur.rowcount > 0

    @staticmethod
    def _valider_meuble(piece: dict, meuble: dict) -> None:
        if meuble["largeur"] <= 0 or meuble["profondeur"] <= 0 or meuble["hauteur"] <= 0:
            raise ValueError("Les dimensions du meuble doivent être positives.")
        demi_x = meuble["largeur"] / 2
        demi_z = meuble["profondeur"] / 2
        if abs(meuble["position_x"]) + demi_x > piece["largeur"] / 2 or abs(meuble["position_z"]) + demi_z > piece["profondeur"] / 2:
            raise ValueError("Le meuble doit rester entièrement dans la pièce.")
        if meuble["hauteur"] > piece["hauteur"]:
            raise ValueError("Le meuble ne peut pas dépasser la hauteur de la pièce.")

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
                    (piece_id, type, mur, position, largeur, hauteur, hauteur_appui, sens_ouverture, angle_ouverture)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                piece_id, donnees["type"], donnees["mur"], donnees["position"],
                donnees["largeur"], donnees["hauteur"], donnees["hauteur_appui"],
                donnees.get("sens_ouverture", "gauche"), donnees.get("angle_ouverture", 90),
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
                SET type = ?, mur = ?, position = ?, largeur = ?, hauteur = ?, hauteur_appui = ?, sens_ouverture = ?, angle_ouverture = ?
                WHERE id = ? AND piece_id = ?
            """, (
                donnees["type"], donnees["mur"], donnees["position"], donnees["largeur"],
                donnees["hauteur"], donnees["hauteur_appui"], donnees.get("sens_ouverture", "gauche"),
                donnees.get("angle_ouverture", 90), ouverture_id, piece_id,
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



    def lister_installations(self, piece_id: str) -> list[dict]:
        with sqlite3.connect(self.db_path) as connexion:
            connexion.row_factory = sqlite3.Row
            lignes = connexion.execute("SELECT * FROM elements_installation_3d WHERE piece_id=? ORDER BY id", (piece_id,)).fetchall()
        return [dict(ligne) for ligne in lignes]

    def ajouter_installation(self, piece_id: str, donnees: dict) -> dict | None:
        piece = self.pieces.obtenir(piece_id)
        if piece is None:
            return None
        self._valider_installation(piece, donnees)
        with sqlite3.connect(self.db_path) as connexion:
            curseur = connexion.execute("""INSERT INTO elements_installation_3d
                (piece_id,type,position_x,position_z,hauteur,orientation,circuit,appareil_id)
                VALUES (?,?,?,?,?,?,?,?)""", (piece_id, donnees["type"], donnees["position_x"], donnees["position_z"], donnees["hauteur"], donnees["orientation"], donnees["circuit"].strip(), donnees["appareil_id"]))
            identifiant = curseur.lastrowid
        return next(item for item in self.lister_installations(piece_id) if item["id"] == identifiant)

    def modifier_installation(self, piece_id: str, element_id: int, donnees: dict) -> dict | None:
        piece = self.pieces.obtenir(piece_id)
        if piece is None:
            return None
        self._valider_installation(piece, donnees)
        with sqlite3.connect(self.db_path) as connexion:
            curseur = connexion.execute("""UPDATE elements_installation_3d SET type=?,position_x=?,position_z=?,hauteur=?,orientation=?,circuit=?,appareil_id=? WHERE id=? AND piece_id=?""",
                (donnees["type"], donnees["position_x"], donnees["position_z"], donnees["hauteur"], donnees["orientation"], donnees["circuit"].strip(), donnees["appareil_id"], element_id, piece_id))
        return next((item for item in self.lister_installations(piece_id) if item["id"] == element_id), None) if curseur.rowcount else None

    def supprimer_installation(self, piece_id: str, element_id: int) -> bool:
        with sqlite3.connect(self.db_path) as connexion:
            curseur = connexion.execute("DELETE FROM elements_installation_3d WHERE id=? AND piece_id=?", (element_id, piece_id))
        return curseur.rowcount > 0

    @staticmethod
    def _valider_installation(piece: dict, element: dict) -> None:
        if abs(element["position_x"]) > piece["largeur"] / 2 or abs(element["position_z"]) > piece["profondeur"] / 2:
            raise ValueError("L'élément doit rester dans les limites de la pièce.")
        if element["hauteur"] > piece["hauteur"]:
            raise ValueError("La hauteur dépasse celle de la pièce.")
        if not element["circuit"].strip():
            raise ValueError("Le nom du circuit est obligatoire.")
