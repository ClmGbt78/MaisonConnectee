import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "systeme_historique.db"

APPAREILS_INITIAUX = [
    ("lampe-salon", "Lampe du salon", "Salon", "lumiere", 0),
    ("ventilateur", "Ventilateur", "Chambre", "ventilation", 0),
    ("prise-bureau", "Prise du bureau", "Bureau", "prise", 0),
]


class AppareilRepository:
    """Accès SQLite. Utilise la base existante sans la recréer ni l'effacer."""

    def __init__(self, db_path: Path | str = DB_PATH):
        self.db_path = str(db_path)

    def initialiser(self) -> None:
        with sqlite3.connect(self.db_path) as connexion:
            connexion.execute("""
                CREATE TABLE IF NOT EXISTS appareils_domotiques (
                    id TEXT PRIMARY KEY,
                    nom TEXT NOT NULL,
                    piece TEXT NOT NULL,
                    type TEXT NOT NULL,
                    allume INTEGER NOT NULL DEFAULT 0,
                    luminosite INTEGER
                )
            """)
            colonnes = {ligne[1] for ligne in connexion.execute("PRAGMA table_info(appareils_domotiques)")}
            if "luminosite" not in colonnes:
                # Migration additive : ne modifie ni ne supprime les colonnes existantes.
                connexion.execute("ALTER TABLE appareils_domotiques ADD COLUMN luminosite INTEGER")
            # Les lumières existantes reçoivent une valeur initiale sans écraser les réglages.
            connexion.execute("""
                UPDATE appareils_domotiques SET luminosite = 100
                WHERE type = 'lumiere' AND luminosite IS NULL
            """)
            # INSERT OR IGNORE préserve les appareils et états déjà présents.
            connexion.executemany("""
                INSERT OR IGNORE INTO appareils_domotiques
                    (id, nom, piece, type, allume)
                VALUES (?, ?, ?, ?, ?)
            """, APPAREILS_INITIAUX)

    @staticmethod
    def _convertir(ligne: sqlite3.Row) -> dict:
        appareil = dict(ligne)
        appareil["allume"] = bool(appareil["allume"])
        return appareil

    def lister(self, piece: str | None = None, type_appareil: str | None = None) -> list[dict]:
        requete = "SELECT id, nom, piece, type, allume, luminosite FROM appareils_domotiques"
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
                "SELECT id, nom, piece, type, allume FROM appareils_domotiques WHERE id = ?",
                (appareil_id,),
            ).fetchone()
        return self._convertir(ligne) if ligne is not None else None

    def ajouter(self, appareil: dict) -> dict:
        with sqlite3.connect(self.db_path) as connexion:
            connexion.execute("""
                INSERT INTO appareils_domotiques (id, nom, piece, type, allume, luminosite)
                VALUES (?, ?, ?, ?, 0, ?)
            """, (appareil["id"], appareil["nom"], appareil["piece"], appareil["type"], 100 if appareil["type"] == "lumiere" else None))
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
