import sqlite3
from datetime import datetime, timezone

from app.core.config import get_settings

DB_PATH = get_settings().accounts_db_file


def initialiser_stockage_notifications() -> None:
    """Crée le stockage des notifications sans modifier les comptes existants."""
    with sqlite3.connect(DB_PATH) as connexion:
        connexion.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                utilisateur_id INTEGER NOT NULL,
                titre TEXT NOT NULL,
                message TEXT NOT NULL,
                categorie TEXT NOT NULL DEFAULT 'systeme',
                priorite TEXT NOT NULL DEFAULT 'info',
                cree_le TEXT NOT NULL,
                lu_le TEXT
            )
        """)
        connexion.execute("""
            CREATE INDEX IF NOT EXISTS idx_notifications_utilisateur_date
            ON notifications(utilisateur_id, cree_le DESC)
        """)
        connexion.execute("""
            CREATE INDEX IF NOT EXISTS idx_notifications_utilisateur_non_lues
            ON notifications(utilisateur_id, lu_le)
        """)


def creer_notification(
    utilisateur_id: int,
    titre: str,
    message: str,
    categorie: str = "systeme",
    priorite: str = "info",
) -> int:
    """Enregistre un événement pour un utilisateur, sans dépendance à un fournisseur externe."""
    cree_le = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(DB_PATH) as connexion:
        curseur = connexion.execute(
            """
            INSERT INTO notifications
                (utilisateur_id, titre, message, categorie, priorite, cree_le)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (utilisateur_id, titre, message, categorie, priorite, cree_le),
        )
        return int(curseur.lastrowid)
