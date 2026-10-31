import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from app.core.security import get_current_user, require_admin
from app.api.domotique import service as service_domotique
from app.domotique.plan_3d_config import ConfigurationPlan3DRepository

router = APIRouter(prefix="/domotique/plan-3d", tags=["Scénarios et finitions 3D"])
repository = ConfigurationPlan3DRepository()
repository.initialiser()


class Finition(BaseModel):
    materiau: str = Field(pattern=r"^(peinture|papier_peint|brique|pierre|bois|enduit|carrelage|parquet|beton|moquette|platre)$")
    couleur: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")


class FinitionsPiece(BaseModel):
    mur_interieur: Finition
    mur_exterieur: Finition
    sol: Finition
    plafond: Finition


class AppareilScenario(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    allume: bool


class Scenario(BaseModel):
    nom: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=240)
    portee: str = Field(pattern=r"^(maison|selection)$")
    appareils: list[AppareilScenario] = Field(default_factory=list, max_length=100)


@router.get("/finitions")
def lister_finitions(utilisateur: dict = Depends(get_current_user)):
    return repository.lister_finitions()


@router.put("/{piece_id}/finitions")
def enregistrer_finitions(piece_id: str, finitions: FinitionsPiece, utilisateur: dict = Depends(require_admin)):
    from app.domotique.pieces import PiecesRepository
    if PiecesRepository().obtenir(piece_id) is None:
        raise HTTPException(status_code=404, detail="Pièce introuvable")
    return repository.enregistrer_finitions(piece_id, finitions.model_dump())


@router.get("/scenarios")
def lister_scenarios(utilisateur: dict = Depends(get_current_user)):
    return repository.lister_scenarios()


@router.post("/scenarios", status_code=201)
def creer_scenario(scenario: Scenario, utilisateur: dict = Depends(require_admin)):
    data = scenario.model_dump()
    data["nom"] = data["nom"].strip()
    if not data["nom"]:
        raise HTTPException(status_code=422, detail="Le nom du scénario est obligatoire")
    if data["portee"] == "selection" and not data["appareils"]:
        raise HTTPException(status_code=422, detail="Sélectionne au moins un appareil")
    if len({item["id"] for item in data["appareils"]}) != len(data["appareils"]):
        raise HTTPException(status_code=422, detail="Un appareil ne peut apparaître qu'une fois")
    for item in data["appareils"]:
        try:
            appareil = service_domotique.obtenir(item["id"])
        except Exception:
            raise HTTPException(status_code=404, detail=f"Appareil introuvable : {item['id']}")
        if appareil["type"] == "capteur":
            raise HTTPException(status_code=422, detail="Les capteurs sont en lecture seule")
    try:
        return repository.ajouter_scenario(data)
    except sqlite3.IntegrityError as erreur:
        raise HTTPException(status_code=409, detail="Un scénario porte déjà ce nom") from erreur


@router.put("/scenarios/{scenario_id}")
def modifier_scenario(scenario_id: int, scenario: Scenario, utilisateur: dict = Depends(require_admin)):
    data = scenario.model_dump()
    data["nom"] = data["nom"].strip()
    if not data["nom"] or (data["portee"] == "selection" and not data["appareils"]):
        raise HTTPException(status_code=422, detail="Nom et appareils sélectionnés obligatoires")
    if len({item["id"] for item in data["appareils"]}) != len(data["appareils"]):
        raise HTTPException(status_code=422, detail="Un appareil ne peut apparaître qu'une fois")
    for item in data["appareils"]:
        try:
            appareil = service_domotique.obtenir(item["id"])
        except Exception:
            raise HTTPException(status_code=404, detail=f"Appareil introuvable : {item['id']}")
        if appareil["type"] == "capteur":
            raise HTTPException(status_code=422, detail="Les capteurs sont en lecture seule")
    try:
        resultat = repository.modifier_scenario(scenario_id, data)
    except sqlite3.IntegrityError as erreur:
        raise HTTPException(status_code=409, detail="Un scénario porte déjà ce nom") from erreur
    if resultat is None:
        raise HTTPException(status_code=404, detail="Scénario introuvable")
    return resultat


@router.delete("/scenarios/{scenario_id}", status_code=204)
def supprimer_scenario(scenario_id: int, utilisateur: dict = Depends(require_admin)):
    if not repository.supprimer_scenario(scenario_id):
        raise HTTPException(status_code=404, detail="Scénario introuvable")
    return Response(status_code=204)


@router.post("/scenarios/{scenario_id}/appliquer")
def appliquer_scenario(scenario_id: int, utilisateur: dict = Depends(get_current_user)):
    scenario = next((item for item in repository.lister_scenarios() if item["id"] == scenario_id), None)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scénario introuvable")
    appareils = service_domotique.lister()
    if scenario["portee"] == "maison":
        cibles = [item for item in appareils if item["type"] != "capteur"]
        etats = {item["id"]: False for item in cibles}
    else:
        etats = {item["id"]: item["allume"] for item in scenario["appareils"]}
        cibles = [item for item in appareils if item["id"] in etats]
    erreurs = []
    appliques = []
    for appareil in cibles:
        cible = etats.get(appareil["id"], False)
        if scenario["portee"] == "maison":
            cible = next((item["allume"] for item in scenario["appareils"] if item["id"] == appareil["id"]), False)
        try:
            service_domotique.commander(appareil["id"], cible)
            appliques.append(appareil["id"])
        except Exception as erreur:
            erreurs.append({"appareil_id": appareil["id"], "detail": str(erreur)})
    return {"scenario_id": scenario_id, "appliques": appliques, "erreurs": erreurs}
