import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from app.core.config import get_settings
from app.core.security import get_current_user

router = APIRouter(prefix="/notifications", tags=["Notifications"])
DB_PATH = get_settings().accounts_db_file


def _lister(utilisateur_id: int, limite: int, non_lues: bool = False) -> list[dict]:
    requete = """
        SELECT id, titre, message, categorie, priorite, cree_le, lu_le
        FROM notifications
        WHERE utilisateur_id = ?
    """
    parametres: list[object] = [utilisateur_id]
    if non_lues:
        requete += " AND lu_le IS NULL"
    requete += " ORDER BY cree_le DESC, id DESC LIMIT ?"
    parametres.append(limite)
    with sqlite3.connect(DB_PATH) as connexion:
        connexion.row_factory = sqlite3.Row
        lignes = connexion.execute(requete, parametres).fetchall()
    return [dict(ligne) for ligne in lignes]


@router.get("")
def lister_notifications(
    non_lues: bool = Query(default=False),
    limite: int = Query(default=100, ge=1, le=200),
    utilisateur: dict = Depends(get_current_user),
):
    return _lister(int(utilisateur["id"]), limite, non_lues)


@router.post("/lues")
def marquer_toutes_comme_lues(utilisateur: dict = Depends(get_current_user)):
    maintenant = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(DB_PATH) as connexion:
        curseur = connexion.execute(
            """
            UPDATE notifications SET lu_le = ?
            WHERE utilisateur_id = ? AND lu_le IS NULL
            """,
            (maintenant, int(utilisateur["id"])),
        )
    return {"modifiees": curseur.rowcount}


@router.patch("/{notification_id}/lue")
def marquer_comme_lue(
    notification_id: int,
    utilisateur: dict = Depends(get_current_user),
):
    maintenant = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(DB_PATH) as connexion:
        curseur = connexion.execute(
            """
            UPDATE notifications SET lu_le = ?
            WHERE id = ? AND utilisateur_id = ?
            """,
            (maintenant, notification_id, int(utilisateur["id"])),
        )
    if curseur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Notification introuvable")
    return {"id": notification_id, "lu_le": maintenant}


@router.delete("/{notification_id}", status_code=204)
def supprimer_notification(
    notification_id: int,
    utilisateur: dict = Depends(get_current_user),
):
    with sqlite3.connect(DB_PATH) as connexion:
        curseur = connexion.execute(
            "DELETE FROM notifications WHERE id = ? AND utilisateur_id = ?",
            (notification_id, int(utilisateur["id"])),
        )
    if curseur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Notification introuvable")
    return Response(status_code=204)
