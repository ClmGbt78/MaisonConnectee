from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.rgb import router as rgb_router
from app.api.routes import router
from app.core.config import get_settings
from app.api.domotique import router as domotique_router
from app.api.pieces import router as pieces_router
from app.api.plan_3d import router as plan_3d_router
from app.api.plan_3d_config import router as plan_3d_config_router
from app.api.meubles_3d import router as meubles_3d_router
from app.api.comptes import router as comptes_router
from app.api.automatisations import router as automatisations_router, automatisations\nfrom app.api.evolutions import router as evolutions_router
from app.domotique.automations import MoteurAutomatisations
from app.api.domotique import service as service_domotique

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="API centrale de mon assistant personnel",
    version=settings.app_version,
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
app.include_router(automatisations_router, prefix="/api")\napp.include_router(evolutions_router, prefix="/api")

moteur_automatisations = MoteurAutomatisations(automatisations, service_domotique)


@app.on_event("startup")
async def demarrer_automatisations():
    await moteur_automatisations.demarrer()


@app.on_event("shutdown")
async def arreter_automatisations():
    await moteur_automatisations.arreter()