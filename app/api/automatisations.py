import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from app.core.security import get_current_user
from app.api.domotique import repository as scene_repository
from app.domotique.automations import AutomatisationRepository

router = APIRouter(prefix="/domotique/automatisations", tags=["Automatisations"])
automatisations = AutomatisationRepository()
automatisations.initialiser()


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
