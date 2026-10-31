import asyncio
import sqlite3
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.backups import GestionnaireSauvegardes
from app.core.config import get_settings
from app.core.security import require_admin
from app.core.notifications import creer_notification, initialiser_stockage_notifications
from app.api.dashboard import initialiser_stockage_dashboard
from app.core.usb_backups import GestionnaireCopieUSB

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
        sauvegarde = await asyncio.to_thread(gestionnaire.creer_sauvegarde)
        settings = get_settings()
        if settings.usb_backup_mount_path is not None:
            try:
                copie = GestionnaireCopieUSB(
                    settings.usb_backup_mount_path, gestionnaire.dossier_sauvegardes
                )
                resultat = await asyncio.to_thread(copie.copier_sauvegardes)
                sauvegarde["copie_usb"] = "effectuee"
                sauvegarde["sauvegardes_copiees_usb"] = resultat["copiees"]
            except (OSError, RuntimeError) as erreur:
                # La sauvegarde locale reste valide même si la clé est absente.
                sauvegarde["copie_usb"] = "indisponible"
                sauvegarde["detail_copie_usb"] = str(erreur)
        creer_notification(
            int(administrateur["id"]),
            "Sauvegarde créée",
            "Une sauvegarde manuelle des bases MaisonConnectée a été créée.",
            "sauvegarde",
            "success",
        )
        return sauvegarde
    except (OSError, ValueError, sqlite3.Error) as erreur:
        creer_notification(
            int(administrateur["id"]),
            "Échec de sauvegarde",
            "La création de la sauvegarde manuelle a échoué.",
            "sauvegarde",
            "critical",
        )
        raise HTTPException(status_code=500, detail="Impossible de créer la sauvegarde SQLite.") from erreur


@router.post("/{identifiant}/restaurer")
async def restaurer_sauvegarde(
    identifiant: str,
    administrateur: dict = Depends(require_admin),
):
    try:
        gestionnaire = obtenir_gestionnaire()
        resultat = await asyncio.to_thread(gestionnaire.restaurer, identifiant)
        # Une ancienne sauvegarde peut précéder l'ajout de ces tables.
        initialiser_stockage_dashboard()
        initialiser_stockage_notifications()
        creer_notification(
            int(administrateur["id"]),
            "Restauration terminée",
            f"La sauvegarde « {identifiant} » a été restaurée.",
            "sauvegarde",
            "warning",
        )
        return resultat
    except ValueError as erreur:
        raise HTTPException(status_code=404, detail=str(erreur)) from erreur
    except (OSError, sqlite3.Error) as erreur:
        creer_notification(
            int(administrateur["id"]),
            "Échec de restauration",
            f"La restauration de la sauvegarde « {identifiant} » a échoué.",
            "sauvegarde",
            "critical",
        )
        raise HTTPException(status_code=500, detail="Échec de la restauration SQLite.") from erreur
