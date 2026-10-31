from fastapi import APIRouter, Depends, HTTPException, Query, Response
import re
import sqlite3
from pydantic import BaseModel, Field

from app.core.security import get_current_user, require_admin
from app.domotique.adapters.simulation import AdaptateurSimulation
from app.domotique.repository import AppareilRepository
from app.domotique.service import (
    AppareilIntrouvable,
    AppareilService,
    CommandeNonSupportee,
    ErreurAdaptateur,
    TypeAppareilInvalide,
)

router = APIRouter(prefix="/domotique", tags=["Domotique"])

# Même fichier SQLite que la version précédente : aucune migration destructive.
repository = AppareilRepository()
service = AppareilService(repository, AdaptateurSimulation())


def initialiser_stockage() -> None:
    """Initialise le stockage domotique au démarrage de l'application."""
    repository.initialiser()


class CommandeAppareil(BaseModel):
    allume: bool


class ReglageLuminosite(BaseModel):
    luminosite: int = Field(ge=0, le=100)


class ReglageTemperatureCouleur(BaseModel):
    temperature_couleur: int = Field(ge=2700, le=6500)


class ReglageCouleur(BaseModel):
    couleur: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")


class SceneLumineuse(BaseModel):
    nom: str = Field(min_length=1, max_length=80)
    luminosite: int = Field(ge=0, le=100)
    temperature_couleur: int = Field(ge=2700, le=6500)
    couleur: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")


class NouvelAppareil(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    nom: str = Field(min_length=1, max_length=120)
    piece: str = Field(min_length=1, max_length=100)
    type: str = Field(min_length=1, max_length=40)


def _normaliser_appareil(appareil: NouvelAppareil) -> dict:
    return {
        "id": appareil.id.strip(),
        "nom": appareil.nom.strip(),
        "piece": appareil.piece.strip(),
        "type": appareil.type.strip().lower(),
    }


def _erreur_introuvable() -> HTTPException:
    return HTTPException(status_code=404, detail="Appareil introuvable")


@router.get("/appareils")
def obtenir_appareils(
    piece: str | None = Query(default=None, max_length=100),
    type: str | None = Query(default=None, max_length=40),
    utilisateur_connecte: dict = Depends(get_current_user),
):
    return service.lister(
        piece=piece.strip() if piece and piece.strip() else None,
        type_appareil=type.strip().lower() if type and type.strip() else None,
    )


@router.post("/appareils", status_code=201)
def ajouter_appareil(
    nouvel_appareil: NouvelAppareil,
    utilisateur_connecte: dict = Depends(require_admin),
):
    donnees = _normaliser_appareil(nouvel_appareil)
    if not donnees["id"] or not donnees["nom"] or not donnees["piece"]:
        raise HTTPException(
            status_code=422,
            detail="L'identifiant, le nom et la pièce sont obligatoires",
        )
    try:
        return service.ajouter(donnees)
    except TypeAppareilInvalide:
        raise HTTPException(
            status_code=422,
            detail="Type invalide. Types autorisés : lumiere, ventilation, prise, capteur",
        )
    except ValueError as erreur:
        raise HTTPException(status_code=409, detail=str(erreur)) from erreur


@router.delete("/appareils/{appareil_id}", status_code=204)
def supprimer_appareil(
    appareil_id: str,
    utilisateur_connecte: dict = Depends(require_admin),
):
    try:
        service.supprimer(appareil_id)
    except AppareilIntrouvable:
        raise _erreur_introuvable()
    return Response(status_code=204)


@router.get("/appareils/{appareil_id}")
def obtenir_appareil(
    appareil_id: str,
    utilisateur_connecte: dict = Depends(get_current_user),
):
    try:
        return service.obtenir(appareil_id)
    except AppareilIntrouvable:
        raise _erreur_introuvable()


@router.patch("/appareils/{appareil_id}")
def modifier_appareil(
    appareil_id: str,
    commande: CommandeAppareil,
    utilisateur_connecte: dict = Depends(get_current_user),
):
    try:
        return service.commander(appareil_id, commande.allume)
    except AppareilIntrouvable:
        raise _erreur_introuvable()
    except CommandeNonSupportee:
        raise HTTPException(
            status_code=409,
            detail="Cet appareil est en lecture seule et ne peut pas être commandé",
        )
    except ErreurAdaptateur:
        raise HTTPException(
            status_code=503,
            detail="Le pilote domotique n’a pas pu appliquer la commande",
        )


@router.patch("/appareils/{appareil_id}/luminosite")
def regler_luminosite(
    appareil_id: str,
    reglage: ReglageLuminosite,
    utilisateur_connecte: dict = Depends(get_current_user),
):
    try:
        return service.regler_luminosite(appareil_id, reglage.luminosite)
    except AppareilIntrouvable:
        raise _erreur_introuvable()
    except CommandeNonSupportee:
        raise HTTPException(
            status_code=409,
            detail="La luminosité n’est pas prise en charge par cet appareil",
        )
    except ErreurAdaptateur:
        raise HTTPException(
            status_code=503,
            detail="Le pilote domotique n’a pas pu appliquer la luminosité",
        )


@router.patch("/appareils/{appareil_id}/temperature-couleur")
def regler_temperature_couleur(
    appareil_id: str,
    reglage: ReglageTemperatureCouleur,
    utilisateur_connecte: dict = Depends(get_current_user),
):
    try:
        return service.regler_temperature_couleur(appareil_id, reglage.temperature_couleur)
    except AppareilIntrouvable:
        raise _erreur_introuvable()
    except CommandeNonSupportee:
        raise HTTPException(
            status_code=409,
            detail="La température de couleur n’est pas prise en charge par cet appareil",
        )
    except ErreurAdaptateur:
        raise HTTPException(
            status_code=503,
            detail="Le pilote domotique n’a pas pu appliquer la température de couleur",
        )


@router.patch("/appareils/{appareil_id}/couleur")
def regler_couleur(
    appareil_id: str,
    reglage: ReglageCouleur,
    utilisateur_connecte: dict = Depends(get_current_user),
):
    try:
        return service.regler_couleur(appareil_id, reglage.couleur)
    except AppareilIntrouvable:
        raise _erreur_introuvable()
    except CommandeNonSupportee:
        raise HTTPException(
            status_code=409,
            detail="La couleur RGB n’est pas prise en charge par cet appareil",
        )
    except ErreurAdaptateur:
        raise HTTPException(
            status_code=503,
            detail="Le pilote domotique n’a pas pu appliquer la couleur",
        )


@router.get("/scenes")
def lister_scenes(utilisateur_connecte: dict = Depends(get_current_user)):
    return repository.lister_scenes()


@router.post("/scenes", status_code=201)
def creer_scene(
    scene: SceneLumineuse,
    utilisateur_connecte: dict = Depends(get_current_user),
):
    nom = scene.nom.strip()
    if not nom:
        raise HTTPException(status_code=422, detail="Le nom de la scène est obligatoire")
    identifiant = re.sub(r"[^a-z0-9]+", "-", nom.lower()).strip("-")
    if not identifiant:
        raise HTTPException(status_code=422, detail="Nom de scène invalide")
    donnees = {
        "id": identifiant,
        "nom": nom,
        "luminosite": scene.luminosite,
        "temperature_couleur": scene.temperature_couleur,
        "couleur": scene.couleur.upper(),
    }
    try:
        return repository.ajouter_scene(donnees)
    except sqlite3.IntegrityError as erreur:
        raise HTTPException(status_code=409, detail="Une scène portant ce nom existe déjà") from erreur


@router.delete("/scenes/{scene_id}", status_code=204)
def supprimer_scene(
    scene_id: str,
    utilisateur_connecte: dict = Depends(get_current_user),
):
    if not repository.supprimer_scene(scene_id):
        raise HTTPException(status_code=404, detail="Scène lumineuse introuvable")
    return Response(status_code=204)


@router.post("/scenes/{scene_id}/appliquer")
def appliquer_scene(
    scene_id: str,
    utilisateur_connecte: dict = Depends(get_current_user),
):
    try:
        return service.appliquer_scene(scene_id)
    except AppareilIntrouvable:
        raise HTTPException(status_code=404, detail="Scène lumineuse introuvable")
    except CommandeNonSupportee:
        raise HTTPException(status_code=409, detail="Aucune lumière n’est disponible")
    except ErreurAdaptateur:
        raise HTTPException(status_code=503, detail="Le pilote n’a pas pu appliquer complètement la scène")
