from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from app.core.security import require_admin
from app.domotique.plan_3d import Plan3DRepository

router = APIRouter(prefix="/domotique/plan-3d", tags=["Mobilier 3D"])
repository = Plan3DRepository()


class Meuble3D(BaseModel):
    type: str = Field(pattern=r"^(canape|fauteuil|table|lit|armoire|cuisine)$")
    position_x: float = Field(ge=-15, le=15)
    position_z: float = Field(ge=-15, le=15)
    largeur: float = Field(gt=0.1, le=10)
    profondeur: float = Field(gt=0.1, le=10)
    hauteur: float = Field(gt=0.1, le=5)
    rotation: float = Field(default=0, ge=0, lt=360)


@router.post("/{piece_id}/meubles", status_code=201)
def ajouter_meuble(piece_id: str, meuble: Meuble3D, utilisateur: dict = Depends(require_admin)):
    try:
        resultat = repository.ajouter_meuble(piece_id, meuble.model_dump())
    except ValueError as erreur:
        raise HTTPException(status_code=422, detail=str(erreur)) from erreur
    if resultat is None:
        raise HTTPException(status_code=404, detail="Pièce introuvable")
    return resultat


@router.put("/{piece_id}/meubles/{meuble_id}")
def modifier_meuble(piece_id: str, meuble_id: int, meuble: Meuble3D, utilisateur: dict = Depends(require_admin)):
    try:
        resultat = repository.modifier_meuble(piece_id, meuble_id, meuble.model_dump())
    except ValueError as erreur:
        raise HTTPException(status_code=422, detail=str(erreur)) from erreur
    if resultat is None:
        raise HTTPException(status_code=404, detail="Meuble introuvable")
    return resultat


@router.delete("/{piece_id}/meubles/{meuble_id}", status_code=204)
def supprimer_meuble(piece_id: str, meuble_id: int, utilisateur: dict = Depends(require_admin)):
    if not repository.supprimer_meuble(piece_id, meuble_id):
        raise HTTPException(status_code=404, detail="Meuble introuvable")
    return Response(status_code=204)
