from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.rgb import router as rgb_router
from app.api.routes import router, initialiser_base as initialiser_base_systeme
from app.core.config import get_settings
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

settings = get_settings()
moteur_automatisations = MoteurAutomatisations(automatisations, service_domotique)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Les schémas SQLite sont créés explicitement au démarrage de l'API.
    initialiser_base()
    initialiser_base_systeme()
    initialiser_stockage_domotique()
    initialiser_stockages()
    initialiser_stockage_pieces()
    initialiser_stockage_plan_3d()
    initialiser_stockage_plan_3d_config()

    await moteur_automatisations.demarrer()
    try:
        yield
    finally:
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
