from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.security import get_current_user, require_admin
from app.domotique.plan_3d import Plan3DRepository

router = APIRouter(prefix="/domotique/plan-3d", tags=["Plan 3D"])
repository = Plan3DRepository()
repository.initialiser()


class GeometriePiece(BaseModel):
    position_x: float = Field(ge=-100, le=100)
    position_z: float = Field(ge=-100, le=100)
    largeur: float = Field(ge=1.5, le=30)
    profondeur: float = Field(ge=1.5, le=30)
    hauteur: float = Field(default=2.7, ge=2, le=5)
    etage: int = Field(default=0, ge=0, le=5)


@router.get("")
def lister_geometries(utilisateur: dict = Depends(get_current_user)):
    return repository.lister()


@router.put("/{piece_id}")
def enregistrer_geometrie(
    piece_id: str,
    geometrie: GeometriePiece,
    utilisateur: dict = Depends(require_admin),
):
    resultat = repository.enregistrer(piece_id, geometrie.model_dump())
    if resultat is None:
        raise HTTPException(status_code=404, detail="Pièce introuvable")
    return resultat
