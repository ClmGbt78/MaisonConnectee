import json
import math
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
                    forme_json TEXT,
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
                    type TEXT NOT NULL CHECK (type IN (
                        'canape', 'fauteuil', 'table', 'lit', 'armoire', 'cuisine',
                        'television', 'meuble_tv', 'table_basse', 'chaise', 'bureau',
                        'table_chevet', 'commode'
                    )),
                    position_x REAL NOT NULL DEFAULT 0,
                    position_z REAL NOT NULL DEFAULT 0,
                    largeur REAL NOT NULL,
                    profondeur REAL NOT NULL,
                    hauteur REAL NOT NULL,
                    rotation REAL NOT NULL DEFAULT 0,
                    FOREIGN KEY (piece_id) REFERENCES pieces_domotiques(id) ON DELETE CASCADE
                )
            """)
            # Migration non destructive : conserve les meubles déjà enregistrés
            # tout en élargissant les types autorisés par la contrainte SQLite.
            schema_meubles = connexion.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='meubles_pieces_3d'"
            ).fetchone()
            if schema_meubles and "'television'" not in schema_meubles[0]:
                connexion.execute("DROP TABLE IF EXISTS meubles_pieces_3d_nouveau")
                connexion.execute("""
                    CREATE TABLE meubles_pieces_3d_nouveau (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        piece_id TEXT NOT NULL,
                        type TEXT NOT NULL CHECK (type IN (
                            'canape', 'fauteuil', 'table', 'lit', 'armoire', 'cuisine',
                            'television', 'meuble_tv', 'table_basse', 'chaise', 'bureau',
                            'table_chevet', 'commode'
                        )),
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
                    INSERT INTO meubles_pieces_3d_nouveau
                        (id, piece_id, type, position_x, position_z, largeur, profondeur, hauteur, rotation)
                    SELECT id, piece_id, type, position_x, position_z, largeur, profondeur, hauteur, rotation
                    FROM meubles_pieces_3d
                """)
                connexion.execute("DROP TABLE meubles_pieces_3d")
                connexion.execute("ALTER TABLE meubles_pieces_3d_nouveau RENAME TO meubles_pieces_3d")
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
            colonnes_geometrie = {ligne[1] for ligne in connexion.execute("PRAGMA table_info(geometrie_pieces_3d)")}
            if "forme_json" not in colonnes_geometrie:
                connexion.execute("ALTER TABLE geometrie_pieces_3d ADD COLUMN forme_json TEXT")
            colonnes = {ligne[1] for ligne in connexion.execute("PRAGMA table_info(ouvertures_pieces_3d)")}
            if "sens_ouverture" not in colonnes:
                connexion.execute("ALTER TABLE ouvertures_pieces_3d ADD COLUMN sens_ouverture TEXT NOT NULL DEFAULT 'gauche'")
            if "angle_ouverture" not in colonnes:
                connexion.execute("ALTER TABLE ouvertures_pieces_3d ADD COLUMN angle_ouverture INTEGER NOT NULL DEFAULT 90")

    def importer_plan_rez_de_chaussee(self) -> list[dict]:
        """Cree une premiere reconstruction editable du plan papier fourni.

        Les cotes exterieures lisibles (11,72 x 9,00 m) servent de reference.
        Les pieces sont volontairement rectangulaires et approximatives :
        l'utilisateur peut ensuite affiner les murs, portes et positions dans l'editeur.
        Les pieces existantes ne sont jamais supprimees ni leurs appareils deplaces.
        """
        plan = [
            ("Cage d'escalier", "Emprise de l'ancienne chambre 3", "#8B9BAA", -4.46, -2.40, 2.80, 4.20),
            ("Salon", "Rez-de-chaussée", "#D6B58A", -1.50, -2.40, 3.10, 4.20),
            ("Séjour", "Rez-de-chaussée", "#D6B58A", 2.10, -2.40, 4.10, 4.20),
            ("Garage", "Rez-de-chaussée", "#8796A5", 7.36, -2.50, 3.00, 5.00),
            ("Bains", "Rez-de-chaussée", "#76AFC0", -4.30, 1.10, 2.20, 1.80),
            ("WC", "Rez-de-chaussée", "#76AFC0", -1.90, 1.10, 1.50, 1.50),
            ("Dégagement", "Rez-de-chaussée", "#B5A6C8", 0.00, 0.70, 3.00, 1.50),
            ("Chambre 1-2", "Anciennes chambres 1 et 2 réunies", "#91B78C", -2.90, 3.00, 5.80, 3.00),
            ("Entrée", "Rez-de-chaussée", "#B5A6C8", 1.00, 3.50, 1.80, 2.00),
            ("Cuisine", "Rez-de-chaussée", "#D6B58A", 3.60, 3.00, 2.80, 3.00),
        ]
        existantes = {piece["nom"].casefold(): piece for piece in self.pieces.lister()}
        alias = {"chambre 1-2": ("chambre",), "cage d'escalier": ("chambre 3",)}
        for nom, description, couleur, x, z, largeur, profondeur in plan:
            piece = existantes.get(nom.casefold())
            if piece is None:
                ancien = next((existantes.get(nom_alias) for nom_alias in alias.get(nom.casefold(), ()) if existantes.get(nom_alias)), None)
                if ancien is not None:
                    piece = self.pieces.modifier(ancien["id"], nom, description, couleur)
                    existantes.pop(ancien["nom"].casefold(), None)
                    existantes[nom.casefold()] = piece
            if piece is None:
                try:
                    piece = self.pieces.ajouter(nom, description, couleur)
                except sqlite3.IntegrityError:
                    piece = next((p for p in self.pieces.lister() if p["nom"].casefold() == nom.casefold()), None)
            if piece is None:
                raise ValueError(f"Impossible de creer la piece {nom}.")
            resultat = self.enregistrer(piece["id"], {
                "position_x": x, "position_z": z, "largeur": largeur,
                "profondeur": profondeur, "hauteur": 2.7, "etage": 0, "forme": None,
            })
            if resultat is None:
                raise ValueError(f"Impossible d'enregistrer la geometrie de {nom}.")
        return self.lister()

    def importer_plan_etage(self) -> list[dict]:
        """Crée une première implantation approximative de l'étage d'après le croquis.

        Le croquis indique environ 11,5 m de largeur, avec trois chambres
        (3 m, 4,5 m et 3 m), un escalier d'environ 1 m et une profondeur
        proche de 5 m. Les formes restent éditables dans l'interface.
        """
        plan = [
            ("Chambre 1 étage", "Chambre 1 de l'étage", "#91B78C", -4.25, -1.00, 3.00, 3.00),
            ("Chambre 2 étage", "Chambre 2 de l'étage", "#91B78C", 0.50, -1.00, 4.50, 3.00),
            ("Chambre 3 étage", "Chambre 3 de l'étage", "#91B78C", 4.25, -1.00, 3.00, 3.00),
            ("Dressing étage", "Dressing de l'étage", "#B5A6C8", -2.75, 1.75, 2.00, 2.00),
            ("WC étage", "WC de l'étage", "#76AFC0", -0.90, 1.75, 1.20, 2.00),
            ("Salle de bains étage", "Salle de bains de l'étage", "#76AFC0", 1.10, 1.75, 2.80, 2.00),
            ("Palier et cage d'escalier", "Zone du palier et de l'escalier, sans modèle d'escalier 3D", "#8B9BAA", -2.25, -1.00, 1.00, 3.00),
        ]
        existantes = {piece["nom"].casefold(): piece for piece in self.pieces.lister()}
        for nom, description, couleur, x, z, largeur, profondeur in plan:
            piece = existantes.get(nom.casefold())
            if piece is None:
                try:
                    piece = self.pieces.ajouter(nom, description, couleur)
                except sqlite3.IntegrityError:
                    piece = next((p for p in self.pieces.lister() if p["nom"].casefold() == nom.casefold()), None)
            if piece is None:
                raise ValueError(f"Impossible de créer la pièce {nom}.")
            resultat = self.enregistrer(piece["id"], {
                "position_x": x, "position_z": z, "largeur": largeur,
                "profondeur": profondeur, "hauteur": 2.7, "etage": 1, "forme": None,
            })
            if resultat is None:
                raise ValueError(f"Impossible d'enregistrer la géométrie de {nom}.")
        return self.lister()

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
            if geometrie.get("forme_json"):
                geometrie["forme"] = json.loads(geometrie["forme_json"])
            else:
                geometrie["forme"] = None
            geometrie.pop("forme_json", None)
            resultat.append({**piece, **geometrie, "ouvertures": self._lister_ouvertures(piece["id"]), "meubles": self._lister_meubles(piece["id"]), "installations": self.lister_installations(piece["id"])})
        return resultat

    def enregistrer(self, piece_id: str, donnees: dict) -> dict | None:
        piece = self.pieces.obtenir(piece_id)
        if piece is None:
            return None
        piece_avec_geometrie = {**piece, **donnees}
        forme = donnees.get("forme")
        if forme is not None:
            self._valider_forme(forme)
        for ouverture in self._lister_ouvertures(piece_id):
            self._valider_ouverture(piece_avec_geometrie, ouverture)
        with sqlite3.connect(self.db_path) as connexion:
            connexion.execute("""
                INSERT INTO geometrie_pieces_3d
                    (piece_id, position_x, position_z, largeur, profondeur, hauteur, etage, forme_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(piece_id) DO UPDATE SET
                    position_x = excluded.position_x,
                    position_z = excluded.position_z,
                    largeur = excluded.largeur,
                    profondeur = excluded.profondeur,
                    hauteur = excluded.hauteur,
                    etage = excluded.etage,
                    forme_json = excluded.forme_json
            """, (
                piece_id, donnees["position_x"], donnees["position_z"],
                donnees["largeur"], donnees["profondeur"],
                donnees["hauteur"], donnees["etage"],
                json.dumps(forme, separators=(",", ":")) if forme is not None else None,
            ))
        return next((piece for piece in self.lister() if piece["id"] == piece_id), None)

    @staticmethod
    def _valider_forme(forme: list[dict]) -> None:
        if not isinstance(forme, list) or not 4 <= len(forme) <= 12:
            raise ValueError("Une forme doit contenir entre 4 et 12 sommets.")
        points = []
        for point in forme:
            if not isinstance(point, dict) or not all(k in point for k in ("x", "z")):
                raise ValueError("Chaque sommet doit définir les coordonnées x et z.")
            x, z = float(point["x"]), float(point["z"])
            if not math.isfinite(x) or not math.isfinite(z) or abs(x) > 15 or abs(z) > 15:
                raise ValueError("Les sommets doivent rester dans une zone de 15 mètres autour du centre.")
            points.append((x, z))
        if len(set(points)) != len(points):
            raise ValueError("Deux sommets ne peuvent pas être confondus.")
        aire_doublee = sum(points[i][0] * points[(i + 1) % len(points)][1] - points[(i + 1) % len(points)][0] * points[i][1] for i in range(len(points)))
        if abs(aire_doublee) < 0.5:
            raise ValueError("La surface de la pièce est trop petite.")
        for i, (x1, z1) in enumerate(points):
            x2, z2 = points[(i + 1) % len(points)]
            if math.hypot(x2 - x1, z2 - z1) < 0.5:
                raise ValueError("Chaque mur doit mesurer au moins 50 cm.")
        def orientation(a, b, c):
            return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

        def sur_segment(a, b, point):
            return (
                min(a[0], b[0]) - 1e-9 <= point[0] <= max(a[0], b[0]) + 1e-9
                and min(a[1], b[1]) - 1e-9 <= point[1] <= max(a[1], b[1]) + 1e-9
            )

        def segments_se_croisent(a, b, c, d):
            o1, o2 = orientation(a, b, c), orientation(a, b, d)
            o3, o4 = orientation(c, d, a), orientation(c, d, b)
            if o1 * o2 < 0 and o3 * o4 < 0:
                return True
            return (
                (abs(o1) < 1e-9 and sur_segment(a, b, c))
                or (abs(o2) < 1e-9 and sur_segment(a, b, d))
                or (abs(o3) < 1e-9 and sur_segment(c, d, a))
                or (abs(o4) < 1e-9 and sur_segment(c, d, b))
            )

        n = len(points)
        for i in range(n):
            a, b = points[i], points[(i + 1) % n]
            for j in range(i + 1, n):
                if j in (i, (i + 1) % n) or (j + 1) % n in (i, (i + 1) % n):
                    continue
                d, e = points[j], points[(j + 1) % n]
                if segments_se_croisent(a, b, d, e):
                    raise ValueError("Les murs ne peuvent pas se croiser.")

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
        piece = next((item for item in self.lister() if item["id"] == piece_id), None)
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
        piece = next((item for item in self.lister() if item["id"] == piece_id), None)
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
