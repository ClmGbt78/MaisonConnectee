from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.rgb import router as rgb_router
from app.api.routes import router
from app.core.config import get_settings
from app.api.domotique import router as domotique_router
from app.api.comptes import router as comptes_router

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
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
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
app.include_router(rgb_router, prefix="/api")
app.include_router(comptes_router, prefix="/api")