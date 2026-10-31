import sqlite3
from pathlib import Path

from app.core.config import get_settings

DB_PATH = get_settings().domotique_db_file

APPAREILS_INITIAUX = [
    ("lampe-salon", "Lampe du salon", "Salon", "lumiere", 0),
    ("ventilateur", "Ventilateur", "Chambre", "ventilation", 0),
    ("prise-bureau", "Prise du bureau", "Bureau", "prise", 0),
    ("capteur-luminosite-salon", "Capteur de luminosité", "Salon", "capteur", 0),
    ("detecteur-presence-salon", "Détecteur de présence", "Salon", "capteur", 0),
]


class AppareilRepository:
    """Accès SQLite. Utilise la base existante sans la recréer ni l'effacer."""

    def __init__(self, db_path: Path | str = DB_PATH):
        self.db_path = str(db_path)

    def initialiser(self) -> None:
        with sqlite3.connect(self.db_path) as connexion:
            connexion.execute("""
                CREATE TABLE IF NOT EXISTS scenes_lumineuses (
                    id TEXT PRIMARY KEY,
                    nom TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    luminosite INTEGER NOT NULL,
                    temperature_couleur INTEGER NOT NULL,
                    couleur TEXT NOT NULL
                )
            """)
            connexion.execute("""
                CREATE TABLE IF NOT EXISTS appareils_domotiques (
                    id TEXT PRIMARY KEY,
                    nom TEXT NOT NULL,
                    piece TEXT NOT NULL,
                    type TEXT NOT NULL,
                    allume INTEGER NOT NULL DEFAULT 0,
                    luminosite INTEGER,
                    temperature_couleur INTEGER,
                    couleur TEXT
                )
            """)
            colonnes = {ligne[1] for ligne in connexion.execute("PRAGMA table_info(appareils_domotiques)")}
            if "luminosite" not in colonnes:
                # Migration additive : ne modifie ni ne supprime les colonnes existantes.
                connexion.execute("ALTER TABLE appareils_domotiques ADD COLUMN luminosite INTEGER")
            if "temperature_couleur" not in colonnes:
                connexion.execute("ALTER TABLE appareils_domotiques ADD COLUMN temperature_couleur INTEGER")
            if "couleur" not in colonnes:
                connexion.execute("ALTER TABLE appareils_domotiques ADD COLUMN couleur TEXT")
            # INSERT OR IGNORE préserve les appareils et états déjà présents.
            connexion.executemany("""
                INSERT OR IGNORE INTO appareils_domotiques
                    (id, nom, piece, type, allume)
                VALUES (?, ?, ?, ?, ?)
            """, APPAREILS_INITIAUX)
            # Les lumières existantes reçoivent une valeur initiale sans écraser les réglages.
            connexion.execute("""
                UPDATE appareils_domotiques SET luminosite = 100
                WHERE type = 'lumiere' AND luminosite IS NULL
            """)
            connexion.execute("""
                UPDATE appareils_domotiques SET temperature_couleur = 4000
                WHERE type = 'lumiere' AND temperature_couleur IS NULL
            """)
            connexion.execute("""
                UPDATE appareils_domotiques SET couleur = '#FFFFFF'
                WHERE type = 'lumiere' AND couleur IS NULL
            """)

    @staticmethod
    def _convertir(ligne: sqlite3.Row) -> dict:
        appareil = dict(ligne)
        appareil["allume"] = bool(appareil["allume"])
        return appareil

    def lister(self, piece: str | None = None, type_appareil: str | None = None) -> list[dict]:
        requete = "SELECT id, nom, piece, type, allume, luminosite, temperature_couleur, couleur FROM appareils_domotiques"
        conditions: list[str] = []
        parametres: list[str] = []
        if piece:
            conditions.append("piece = ? COLLATE NOCASE")
            parametres.append(piece)
        if type_appareil:
            conditions.append("type = ? COLLATE NOCASE")
            parametres.append(type_appareil)
        if conditions:
            requete += " WHERE " + " AND ".join(conditions)
        requete += " ORDER BY id"
        with sqlite3.connect(self.db_path) as connexion:
            connexion.row_factory = sqlite3.Row
            lignes = connexion.execute(requete, parametres).fetchall()
        return [self._convertir(ligne) for ligne in lignes]

    def obtenir(self, appareil_id: str) -> dict | None:
        with sqlite3.connect(self.db_path) as connexion:
            connexion.row_factory = sqlite3.Row
            ligne = connexion.execute(
                "SELECT id, nom, piece, type, allume, luminosite, temperature_couleur, couleur FROM appareils_domotiques WHERE id = ?",
                (appareil_id,),
            ).fetchone()
        return self._convertir(ligne) if ligne is not None else None

    def ajouter(self, appareil: dict) -> dict:
        with sqlite3.connect(self.db_path) as connexion:
            connexion.execute("""
                INSERT INTO appareils_domotiques (id, nom, piece, type, allume, luminosite, temperature_couleur, couleur)
                VALUES (?, ?, ?, ?, 0, ?, ?, ?)
            """, (appareil["id"], appareil["nom"], appareil["piece"], appareil["type"], 100 if appareil["type"] == "lumiere" else None, 4000 if appareil["type"] == "lumiere" else None, "#FFFFFF" if appareil["type"] == "lumiere" else None))
        return self.obtenir(appareil["id"])  # type: ignore[return-value]

    def supprimer(self, appareil_id: str) -> bool:
        with sqlite3.connect(self.db_path) as connexion:
            curseur = connexion.execute(
                "DELETE FROM appareils_domotiques WHERE id = ?", (appareil_id,)
            )
            return curseur.rowcount > 0

    def definir_etat(self, appareil_id: str, allume: bool) -> dict | None:
        with sqlite3.connect(self.db_path) as connexion:
            curseur = connexion.execute(
                "UPDATE appareils_domotiques SET allume = ? WHERE id = ?",
                (int(allume), appareil_id),
            )
            if curseur.rowcount == 0:
                return None
        return self.obtenir(appareil_id)

    def definir_luminosite(self, appareil_id: str, luminosite: int) -> dict | None:
        with sqlite3.connect(self.db_path) as connexion:
            curseur = connexion.execute(
                "UPDATE appareils_domotiques SET luminosite = ? WHERE id = ? AND type = 'lumiere'",
                (luminosite, appareil_id),
            )
            if curseur.rowcount == 0:
                return None
        return self.obtenir(appareil_id)

    def definir_temperature_couleur(self, appareil_id: str, temperature_couleur: int) -> dict | None:
        with sqlite3.connect(self.db_path) as connexion:
            curseur = connexion.execute(
                "UPDATE appareils_domotiques SET temperature_couleur = ? WHERE id = ? AND type = 'lumiere'",
                (temperature_couleur, appareil_id),
            )
            if curseur.rowcount == 0:
                return None
        return self.obtenir(appareil_id)


    def definir_couleur(self, appareil_id: str, couleur: str) -> dict | None:
        with sqlite3.connect(self.db_path) as connexion:
            curseur = connexion.execute(
                "UPDATE appareils_domotiques SET couleur = ? WHERE id = ? AND type = 'lumiere'",
                (couleur, appareil_id),
            )
            if curseur.rowcount == 0:
                return None
        return self.obtenir(appareil_id)


    def lister_scenes(self) -> list[dict]:
        with sqlite3.connect(self.db_path) as connexion:
            connexion.row_factory = sqlite3.Row
            lignes = connexion.execute(
                "SELECT id, nom, luminosite, temperature_couleur, couleur FROM scenes_lumineuses ORDER BY nom COLLATE NOCASE"
            ).fetchall()
        return [dict(ligne) for ligne in lignes]

    def obtenir_scene(self, scene_id: str) -> dict | None:
        with sqlite3.connect(self.db_path) as connexion:
            connexion.row_factory = sqlite3.Row
            ligne = connexion.execute(
                "SELECT id, nom, luminosite, temperature_couleur, couleur FROM scenes_lumineuses WHERE id = ?",
                (scene_id,),
            ).fetchone()
        return dict(ligne) if ligne is not None else None

    def ajouter_scene(self, scene: dict) -> dict:
        with sqlite3.connect(self.db_path) as connexion:
            connexion.execute(
                "INSERT INTO scenes_lumineuses (id, nom, luminosite, temperature_couleur, couleur) VALUES (?, ?, ?, ?, ?)",
                (scene["id"], scene["nom"], scene["luminosite"], scene["temperature_couleur"], scene["couleur"]),
            )
        return self.obtenir_scene(scene["id"])  # type: ignore[return-value]

    def supprimer_scene(self, scene_id: str) -> bool:
        with sqlite3.connect(self.db_path) as connexion:
            curseur = connexion.execute("DELETE FROM scenes_lumineuses WHERE id = ?", (scene_id,))
            return curseur.rowcount > 0
