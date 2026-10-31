from fastapi import APIRouter, Depends, HTTPException, Response
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

 
class OuverturePiece(BaseModel):
    type: str = Field(pattern=r"^(porte|fenetre)$")
    mur: str = Field(pattern=r"^(nord|sud|est|ouest)$")
    position: float = Field(default=0, ge=-15, le=15)
    largeur: float = Field(ge=0.4, le=8)
    hauteur: float = Field(ge=0.4, le=4)
    hauteur_appui: float = Field(default=0, ge=0, le=3)
    sens_ouverture: str = Field(default="gauche", pattern=r"^(gauche|droite)$")
    angle_ouverture: int = Field(default=90, ge=0, le=150)


@router.post("/{piece_id}/ouvertures", status_code=201)
def ajouter_ouverture(
    piece_id: str,
    ouverture: OuverturePiece,
    utilisateur: dict = Depends(require_admin),
):
    donnees = ouverture.model_dump()
    try:
        resultat = repository.ajouter_ouverture(piece_id, donnees)
    except ValueError as erreur:
        raise HTTPException(status_code=422, detail=str(erreur)) from erreur
    if resultat is None:
        raise HTTPException(status_code=404, detail="Pièce introuvable")
    return resultat


@router.put("/{piece_id}/ouvertures/{ouverture_id}")
def modifier_ouverture(
    piece_id: str,
    ouverture_id: int,
    ouverture: OuverturePiece,
    utilisateur: dict = Depends(require_admin),
):
    try:
        resultat = repository.modifier_ouverture(piece_id, ouverture_id, ouverture.model_dump())
    except ValueError as erreur:
        raise HTTPException(status_code=422, detail=str(erreur)) from erreur
    if resultat is None:
        raise HTTPException(status_code=404, detail="Ouverture introuvable")
    return resultat


@router.delete("/{piece_id}/ouvertures/{ouverture_id}", status_code=204)
def supprimer_ouverture(
    piece_id: str,
    ouverture_id: int,
    utilisateur: dict = Depends(require_admin),
):
    if not repository.supprimer_ouverture(piece_id, ouverture_id):
        raise HTTPException(status_code=404, detail="Ouverture introuvable")
    return Response(status_code=204)


class ElementInstallation(BaseModel):
    type: str = Field(pattern=r"^(prise|interrupteur|appareil)$")
    position_x: float = Field(ge=-15, le=15)
    position_z: float = Field(ge=-15, le=15)
    hauteur: float = Field(default=0.3, ge=0.05, le=4.5)
    orientation: str = Field(default="nord", pattern=r"^(nord|sud|est|ouest)$")
    circuit: str = Field(default="Circuit général", min_length=1, max_length=80)
    appareil_id: str | None = Field(default=None, max_length=100)


@router.get("/{piece_id}/installations")
def lister_installations(piece_id: str, utilisateur: dict = Depends(get_current_user)):
    return repository.lister_installations(piece_id)


@router.post("/{piece_id}/installations", status_code=201)
def ajouter_installation(piece_id: str, element: ElementInstallation, utilisateur: dict = Depends(require_admin)):
    try:
        resultat = repository.ajouter_installation(piece_id, element.model_dump())
    except ValueError as erreur:
        raise HTTPException(status_code=422, detail=str(erreur)) from erreur
    if resultat is None:
        raise HTTPException(status_code=404, detail="Pièce introuvable")
    return resultat


@router.put("/{piece_id}/installations/{element_id}")
def modifier_installation(piece_id: str, element_id: int, element: ElementInstallation, utilisateur: dict = Depends(require_admin)):
    try:
        resultat = repository.modifier_installation(piece_id, element_id, element.model_dump())
    except ValueError as erreur:
        raise HTTPException(status_code=422, detail=str(erreur)) from erreur
    if resultat is None:
        raise HTTPException(status_code=404, detail="Installation introuvable")
    return resultat


@router.delete("/{piece_id}/installations/{element_id}", status_code=204)
def supprimer_installation(piece_id: str, element_id: int, utilisateur: dict = Depends(require_admin)):
    if not repository.supprimer_installation(piece_id, element_id):
        raise HTTPException(status_code=404, detail="Installation introuvable")
    return Response(status_code=204)
