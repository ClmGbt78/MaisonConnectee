import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.rgb import router as rgb_router
from app.api.routes import router, initialiser_base as initialiser_base_systeme
from app.api.sauvegardes import router as sauvegardes_router, obtenir_gestionnaire
from app.api.dashboard import router as dashboard_router, initialiser_stockage_dashboard
from app.api.notifications import router as notifications_router
from app.core.notifications import initialiser_stockage_notifications
from app.core.config import get_settings
from app.core.usb_backups import GestionnaireCopieUSB
from app.api.domotique import router as domotique_router, initialiser_stockage as initialiser_stockage_domotique
from app.api.pieces import router as pieces_router, initialiser_stockage as initialiser_stockage_pieces
from app.api.plan_3d import router as plan_3d_router, initialiser_stockage as initialiser_stockage_plan_3d
from app.api.plan_3d_config import router as plan_3d_config_router, initialiser_stockage as initialiser_stockage_plan_3d_config
from app.api.meubles_3d import router as meubles_3d_router
from app.api.comptes import router as comptes_router, initialiser_base
from app.api.automatisations import (
    router as automatisations_router,
    automatisations,
    initialiser_stockages,
)
from app.domotique.automations import MoteurAutomatisations
from app.api.domotique import service as service_domotique

logger = logging.getLogger(__name__)
settings = get_settings()
moteur_automatisations = MoteurAutomatisations(automatisations, service_domotique)


async def synchroniser_sauvegardes_usb(gestionnaire):
    if settings.usb_backup_mount_path is None:
        return
    try:
        copie = GestionnaireCopieUSB(
            settings.usb_backup_mount_path, gestionnaire.dossier_sauvegardes
        )
        resultat = await asyncio.to_thread(copie.copier_sauvegardes)
        logger.info("Synchronisation USB : %s copie(s), %s déjà présente(s).",
                    resultat["copiees"], resultat["ignorees"])
    except Exception:
        # Une clé absente ne doit jamais empêcher le démarrage de la domotique.
        logger.exception("Copie des sauvegardes vers la clé USB impossible.")


async def _boucle_sauvegardes_periodiques(gestionnaire):
    while True:
        await asyncio.sleep(settings.backup_interval_hours * 60 * 60)
        try:
            await asyncio.to_thread(gestionnaire.creer_sauvegarde)
            logger.info("Sauvegarde SQLite périodique créée.")
            await synchroniser_sauvegardes_usb(gestionnaire)
        except Exception:
            logger.exception("Échec de la sauvegarde SQLite périodique.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.preparer_stockage()
    from app.core.security import get_jwt_secret
    get_jwt_secret()
    initialiser_base()
    initialiser_stockage_dashboard()
    initialiser_stockage_notifications()
    initialiser_base_systeme()
    initialiser_stockage_domotique()
    initialiser_stockages()
    initialiser_stockage_pieces()
    initialiser_stockage_plan_3d()
    initialiser_stockage_plan_3d_config()

    gestionnaire_sauvegardes = obtenir_gestionnaire()
    try:
        await asyncio.to_thread(gestionnaire_sauvegardes.creer_sauvegarde)
        logger.info("Sauvegarde SQLite initiale créée.")
        await synchroniser_sauvegardes_usb(gestionnaire_sauvegardes)
    except Exception:
        logger.exception("Impossible de créer la sauvegarde SQLite initiale.")

    tache_sauvegardes = asyncio.create_task(
        _boucle_sauvegardes_periodiques(gestionnaire_sauvegardes)
    )
    await moteur_automatisations.demarrer()
    try:
        yield
    finally:
        tache_sauvegardes.cancel()
        try:
            await tache_sauvegardes
        except asyncio.CancelledError:
            pass
        await moteur_automatisations.arreter()


app = FastAPI(
    title=settings.app_name,
    description="API centrale de mon assistant personnel",
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
    allow_headers=["*"],
)

@app.get("/")
def accueil():
    return {
        "projet": "Maison Connectée",
        "etat": "en fonctionnement",
    }


app.include_router(router, prefix="/api")
app.include_router(domotique_router, prefix="/api")
app.include_router(pieces_router, prefix="/api")
app.include_router(plan_3d_router, prefix="/api")
app.include_router(plan_3d_config_router, prefix="/api")
app.include_router(meubles_3d_router, prefix="/api")
app.include_router(rgb_router, prefix="/api")
app.include_router(comptes_router, prefix="/api")
app.include_router(automatisations_router, prefix="/api")
app.include_router(sauvegardes_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(notifications_router, prefix="/api")
