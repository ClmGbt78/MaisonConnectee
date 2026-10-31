import asyncio
import sqlite3
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.backups import GestionnaireSauvegardes
from app.core.config import get_settings
from app.core.security import require_admin

router = APIRouter(prefix="/sauvegardes", tags=["Sauvegardes"])


@lru_cache(maxsize=1)
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
        gestionnaire = obtenir_gestionnaire()
        return await asyncio.to_thread(gestionnaire.creer_sauvegarde)
    except (OSError, ValueError, sqlite3.Error) as erreur:
        raise HTTPException(status_code=500, detail="Impossible de créer la sauvegarde SQLite.") from erreur


@router.post("/{identifiant}/restaurer")
async def restaurer_sauvegarde(
    identifiant: str,
    administrateur: dict = Depends(require_admin),
):
    try:
        gestionnaire = obtenir_gestionnaire()
        return await asyncio.to_thread(gestionnaire.restaurer, identifiant)
    except ValueError as erreur:
        raise HTTPException(status_code=404, detail=str(erreur)) from erreur
    except (OSError, sqlite3.Error) as erreur:
        raise HTTPException(status_code=500, detail="Échec de la restauration SQLite.") from erreur
