import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from app.core.security import get_current_user, require_admin
from app.domotique.pieces import PiecesRepository

router = APIRouter(prefix="/domotique/pieces", tags=["Pièces"])
repository = PiecesRepository()
repository.initialiser()


class DonneesPiece(BaseModel):
    nom: str = Field(min_length=1, max_length=60)
    description: str = Field(default="", max_length=240)
    couleur: str = Field(default="#365B78", pattern=r"^#[0-9A-Fa-f]{6}$")


def normaliser(item: DonneesPiece) -> tuple[str, str, str]:
    nom = item.nom.strip()
    if not nom:
        raise HTTPException(status_code=422, detail="Le nom de la pièce est obligatoire")
    return nom, item.description.strip(), item.couleur.upper()


@router.get("")
def lister_pieces(utilisateur: dict = Depends(get_current_user)):
    return repository.lister()


@router.post("", status_code=201)
def creer_piece(item: DonneesPiece, utilisateur: dict = Depends(require_admin)):
    nom, description, couleur = normaliser(item)
    try:
        return repository.ajouter(nom, description, couleur)
    except sqlite3.IntegrityError as erreur:
        raise HTTPException(status_code=409, detail="Une pièce portant ce nom existe déjà") from erreur


@router.patch("/{piece_id}")
def modifier_piece(piece_id: str, item: DonneesPiece, utilisateur: dict = Depends(require_admin)):
    nom, description, couleur = normaliser(item)
    try:
        resultat = repository.modifier(piece_id, nom, description, couleur)
    except sqlite3.IntegrityError as erreur:
        raise HTTPException(status_code=409, detail="Une pièce portant ce nom existe déjà") from erreur
    if resultat is None:
        raise HTTPException(status_code=404, detail="Pièce introuvable")
    return resultat


@router.delete("/{piece_id}", status_code=204)
def supprimer_piece(piece_id: str, utilisateur: dict = Depends(require_admin)):
    try:
        nom = repository.supprimer(piece_id)
    except ValueError as erreur:
        raise HTTPException(status_code=409, detail=str(erreur)) from erreur
    if nom is None:
        raise HTTPException(status_code=404, detail="Pièce introuvable")
    return Response(status_code=204)
