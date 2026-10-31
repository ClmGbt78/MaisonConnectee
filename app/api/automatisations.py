import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from app.core.security import get_current_user
from app.api.domotique import repository as scene_repository, service as service_domotique
from app.domotique.automations import AutomatisationRepository
from app.domotique.adapters.ports_serie import lister_ports_disponibles
from app.domotique.configuration_capteurs import ConfigurationCapteursRepository

router = APIRouter(prefix="/domotique/automatisations", tags=["Automatisations"])
automatisations = AutomatisationRepository()
automatisations.initialiser()
configurations_capteurs = ConfigurationCapteursRepository()
configurations_capteurs.initialiser()


class NouvelleAutomatisation(BaseModel):
    nom: str = Field(min_length=1, max_length=80)
    heure: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    jours: list[int] = Field(min_length=1, max_length=7)
    scene_id: str = Field(min_length=1, max_length=100)
    piece: str | None = Field(default=None, max_length=100)
    extinction_minutes: int | None = Field(default=None, ge=1, le=1440)


class EtatAutomatisation(BaseModel):
    active: bool


@router.get("")
def lister_automatisations(utilisateur: dict = Depends(get_current_user)):
    return automatisations.lister()


@router.post("", status_code=201)
def creer_automatisation(
    item: NouvelleAutomatisation,
    utilisateur: dict = Depends(get_current_user),
):
    nom = item.nom.strip()
    piece = item.piece.strip() if item.piece and item.piece.strip() else None
    if not nom:
        raise HTTPException(status_code=422, detail="Le nom est obligatoire")
    if any(jour not in range(1, 8) for jour in item.jours) or len(set(item.jours)) != len(item.jours):
        raise HTTPException(status_code=422, detail="Les jours doivent être uniques et compris entre 1 et 7")
    if scene_repository.obtenir_scene(item.scene_id) is None:
        raise HTTPException(status_code=404, detail="Scène lumineuse introuvable")
    if piece and not scene_repository.lister(piece=piece, type_appareil="lumiere"):
        raise HTTPException(status_code=422, detail="Aucune lumière n'est enregistrée dans cette pièce")
    try:
        return automatisations.ajouter({
            "nom": nom,
            "heure": item.heure,
            "jours": sorted(item.jours),
            "scene_id": item.scene_id,
            "piece": piece,
            "extinction_minutes": item.extinction_minutes,
        })
    except sqlite3.IntegrityError as erreur:
        raise HTTPException(status_code=409, detail="Impossible de créer cette automatisation") from erreur


@router.patch("/{automation_id}")
def modifier_automatisation(
    automation_id: str,
    etat: EtatAutomatisation,
    utilisateur: dict = Depends(get_current_user),
):
    resultat = automatisations.modifier_active(automation_id, etat.active)
    if resultat is None:
        raise HTTPException(status_code=404, detail="Automatisation introuvable")
    return resultat


@router.delete("/{automation_id}", status_code=204)
def supprimer_automatisation(
    automation_id: str,
    utilisateur: dict = Depends(get_current_user),
):
    if not automatisations.supprimer(automation_id):
        raise HTTPException(status_code=404, detail="Automatisation introuvable")
    return Response(status_code=204)


class NouvelleConditionnelle(BaseModel):
    nom: str = Field(min_length=1, max_length=80)
    capteur_id: str = Field(min_length=1, max_length=100)
    condition: str = Field(pattern=r"^(luminosite_inferieure|presence_detectee|absence_prolongee)$")
    seuil: float | None = Field(default=None, ge=0, le=2000)
    duree_absence: int | None = Field(default=None, ge=1, le=1440)
    scene_id: str | None = Field(default=None, max_length=100)
    piece: str | None = Field(default=None, max_length=100)


class MesureSimulee(BaseModel):
    type_mesure: str = Field(pattern=r"^(luminosite|presence|temperature)$")
    valeur: float = Field(ge=-20, le=2000)


@router.get("/ports-serie")
def obtenir_ports_serie(utilisateur: dict = Depends(get_current_user)):
    try:
        return lister_ports_disponibles()
    except RuntimeError as erreur:
        raise HTTPException(status_code=503, detail=str(erreur)) from erreur


@router.get("/capteurs")
def lister_capteurs(utilisateur: dict = Depends(get_current_user)):
    mesures = {item["appareil_id"]: item for item in automatisations.lister_mesures()}
    capteurs = service_domotique.lister(type_appareil="capteur")
    return [{**capteur, "mesure": mesures.get(capteur["id"])} for capteur in capteurs]


@router.put("/capteurs/{capteur_id}/mesure")
def simuler_mesure_capteur(
    capteur_id: str,
    mesure: MesureSimulee,
    utilisateur: dict = Depends(get_current_user),
):
    try:
        capteur = service_domotique.obtenir(capteur_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Capteur introuvable")
    if capteur["type"] != "capteur":
        raise HTTPException(status_code=409, detail="Cet appareil n'est pas un capteur")
    if mesure.type_mesure == "luminosite" and not 0 <= mesure.valeur <= 100:
        raise HTTPException(status_code=422, detail="La luminosité doit être comprise entre 0 et 100")
    if mesure.type_mesure == "temperature" and not -20 <= mesure.valeur <= 80:
        raise HTTPException(status_code=422, detail="La température doit être comprise entre -20 et 80 °C")
    if mesure.type_mesure == "presence" and mesure.valeur not in (0, 1):
        raise HTTPException(status_code=422, detail="La présence doit valoir 0 (absent) ou 1 (présent)")
    resultat = automatisations.enregistrer_mesure(capteur_id, mesure.type_mesure, mesure.valeur)\n    from app.domotique.evolutions import evolutions\n    if mesure.type_mesure == "temperature":\n        evolutions.enregistrer(capteur_id, "temperature_mesuree", mesure.valeur, "°C")\n    return resultat


@router.get("/conditionnelles")
def lister_conditionnelles(utilisateur: dict = Depends(get_current_user)):
    return automatisations.lister_conditionnelles()


@router.post("/conditionnelles", status_code=201)
def creer_conditionnelle(
    item: NouvelleConditionnelle,
    utilisateur: dict = Depends(get_current_user),
):
    nom = item.nom.strip()
    piece = item.piece.strip() if item.piece and item.piece.strip() else None
    if not nom:
        raise HTTPException(status_code=422, detail="Le nom est obligatoire")
    try:
        capteur = service_domotique.obtenir(item.capteur_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Capteur introuvable")
    if capteur["type"] != "capteur":
        raise HTTPException(status_code=409, detail="L'appareil sélectionné n'est pas un capteur")
    mesures = {m["appareil_id"]: m for m in automatisations.lister_mesures()}
    mesure = mesures.get(item.capteur_id)
    type_attendu = "luminosite" if item.condition == "luminosite_inferieure" else "presence"
    if mesure is None:
        raise HTTPException(status_code=422, detail="Simule une première mesure du capteur avant de créer la règle")
    if mesure["type_mesure"] != type_attendu:
        raise HTTPException(status_code=422, detail="Le type de mesure ne correspond pas à la condition")
    if item.condition == "luminosite_inferieure":
        if item.seuil is None or item.scene_id is None:
            raise HTTPException(status_code=422, detail="Un seuil et une scène sont requis pour la luminosité")
        if scene_repository.obtenir_scene(item.scene_id) is None:
            raise HTTPException(status_code=404, detail="Scène lumineuse introuvable")
    elif item.condition == "presence_detectee":
        if item.scene_id is None or scene_repository.obtenir_scene(item.scene_id) is None:
            raise HTTPException(status_code=404, detail="Une scène lumineuse valide est requise")
    elif item.duree_absence is None:
        raise HTTPException(status_code=422, detail="La durée d'absence est obligatoire")
    if piece and not scene_repository.lister(piece=piece, type_appareil="lumiere"):
        raise HTTPException(status_code=422, detail="Aucune lumière n'est enregistrée dans cette pièce")
    return automatisations.ajouter_conditionnelle({
        "nom": nom, "capteur_id": item.capteur_id, "condition": item.condition,
        "seuil": item.seuil, "duree_absence": item.duree_absence,
        "scene_id": item.scene_id, "piece": piece,
    })


@router.patch("/conditionnelles/{automation_id}")
def modifier_conditionnelle(
    automation_id: str,
    etat: EtatAutomatisation,
    utilisateur: dict = Depends(get_current_user),
):
    resultat = automatisations.modifier_conditionnelle(automation_id, etat.active)
    if resultat is None:
        raise HTTPException(status_code=404, detail="Automatisation conditionnelle introuvable")
    return resultat


@router.delete("/conditionnelles/{automation_id}", status_code=204)
def supprimer_conditionnelle(
    automation_id: str,
    utilisateur: dict = Depends(get_current_user),
):
    if not automatisations.supprimer_conditionnelle(automation_id):
        raise HTTPException(status_code=404, detail="Automatisation conditionnelle introuvable")
    return Response(status_code=204)


class ConfigurationSerieCapteur(BaseModel):
    port: str = Field(min_length=1, max_length=32)
    debit: int = Field(default=9600, ge=300, le=2000000)


@router.get("/capteurs/configurations-serie")
def lister_configurations_capteurs(utilisateur: dict = Depends(get_current_user)):
    return configurations_capteurs.lister()


@router.put("/capteurs/{capteur_id}/configuration-serie")
def configurer_port_capteur(
    capteur_id: str,
    configuration: ConfigurationSerieCapteur,
    utilisateur: dict = Depends(get_current_user),
):
    try:
        capteur = service_domotique.obtenir(capteur_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Capteur introuvable")
    if capteur["type"] != "capteur":
        raise HTTPException(status_code=409, detail="L'appareil sélectionné n'est pas un capteur")

    port_demande = configuration.port.strip().upper()
    try:
        ports = lister_ports_disponibles()
    except RuntimeError as erreur:
        raise HTTPException(status_code=503, detail=str(erreur)) from erreur
    if port_demande not in {port["port"].upper() for port in ports}:
        raise HTTPException(status_code=422, detail="Ce port n'est pas détecté actuellement")

    try:
        return configurations_capteurs.enregistrer(capteur_id, port_demande, configuration.debit)
    except sqlite3.IntegrityError as erreur:
        raise HTTPException(status_code=409, detail="Ce port est déjà associé à un autre capteur") from erreur


@router.delete("/capteurs/{capteur_id}/configuration-serie", status_code=204)
def supprimer_configuration_capteur(
    capteur_id: str,
    utilisateur: dict = Depends(get_current_user),
):
    if not configurations_capteurs.supprimer(capteur_id):
        raise HTTPException(status_code=404, detail="Aucune configuration série pour ce capteur")
    return Response(status_code=204)
