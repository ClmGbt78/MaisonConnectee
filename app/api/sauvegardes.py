import asyncio

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.backups import GestionnaireSauvegardes
from app.core.config import get_settings
from app.core.security import require_admin

router = APIRouter(prefix="/sauvegardes", tags=["Sauvegardes"])


def obtenir_gestionnaire() -> GestionnaireSauvegardes:
    settings = get_settings()
    return GestionnaireSauvegardes(
        chemins_bases={
            "comptes.db": settings.accounts_db_file,
            "systeme_historique.db": settings.domotique_db_file,
        },
        dossier_sauvegardes=settings.backup_dir_path,
        retention=settings.backup_retention_count,
    )


@router.get("")
def lister_sauvegardes(administrateur: dict = Depends(require_admin)):
    return obtenir_gestionnaire().lister_sauvegardes()


@router.post("", status_code=status.HTTP_201_CREATED)
async def creer_sauvegarde(administrateur: dict = Depends(require_admin)):
    try:
        return await asyncio.to_thread(obtenir_gestionnaire().creer_sauvegarde)
    except (OSError, ValueError) as erreur:
        raise HTTPException(status_code=500, detail=f"Impossible de créer la sauvegarde : {erreur}") from erreur


@router.post("/{identifiant}/restaurer")
async def restaurer_sauvegarde(
    identifiant: str,
    administrateur: dict = Depends(require_admin),
):
    try:
        return await asyncio.to_thread(obtenir_gestionnaire().restaurer, identifiant)
    except ValueError as erreur:
        raise HTTPException(status_code=404, detail=str(erreur)) from erreur
    except (OSError, sqlite3.Error) as erreur:
        raise HTTPException(status_code=500, detail=f"Échec de la restauration : {erreur}") from erreur
