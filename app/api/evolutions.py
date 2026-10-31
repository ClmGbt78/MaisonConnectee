from datetime import datetime
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.security import get_current_user, require_admin
from app.api.domotique import service
from app.domotique.evolutions import evolutions
from app.domotique.pieces import PiecesRepository

router = APIRouter(prefix="/domotique", tags=["Historique, inventaire et automatisations avancées"])


class MetadonneesAppareil(BaseModel):
    fabricant: str | None = Field(default=None, max_length=100)
    modele: str | None = Field(default=None, max_length=100)
    reference_technique: str | None = Field(default=None, max_length=120)
    protocole: str | None = Field(default=None, max_length=80)
    adresse_materielle: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=1000)


class AffectationPiece(BaseModel):
    piece: str = Field(min_length=1, max_length=100)


class ConditionAvancee(BaseModel):
    appareil_id: str = Field(min_length=1, max_length=100)
    operateur: str = Field(pattern=r"^(<|<=|>|>=|=|!=)$")
    seuil: float = Field(ge=-100000, le=100000)


class ActionAvancee(BaseModel):
    appareil_id: str = Field(min_length=1, max_length=100)
    allume: bool
    delai_secondes: int = Field(default=0, ge=0, le=86400)


class RegleAvancee(BaseModel):
    nom: str = Field(min_length=1, max_length=80)
    logique: str = Field(default="ET", pattern=r"^(ET|OU)$")
    conditions: list[ConditionAvancee] = Field(min_length=1, max_length=10)
    actions: list[ActionAvancee] = Field(min_length=1, max_length=20)
    heure_debut: str | None = Field(default=None, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    heure_fin: str | None = Field(default=None, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    jours: list[int] = Field(default_factory=lambda: [1,2,3,4,5,6,7], min_length=1, max_length=7)


class ActivationRegle(BaseModel):
    active: bool


@router.get("/historique")
def obtenir_historique(
    appareil_id: str | None = None,
    evenement: str | None = None,
    periode: str = Query(default="semaine", pattern=r"^(jour|semaine|mois|tout)$"),
    utilisateur: dict = Depends(get_current_user),
):
    maintenant = datetime.now()
    durees = {"jour": timedelta(days=1), "semaine": timedelta(days=7), "mois": timedelta(days=30), "tout": None}
    depuis = (maintenant - durees[periode]).isoformat(timespec="seconds") if durees[periode] else None
    return evolutions.historique(appareil_id, evenement, depuis)


@router.get("/inventaire")
def obtenir_inventaire(utilisateur: dict = Depends(get_current_user)):
    return evolutions.inventaire(service.lister())


@router.put("/inventaire/{appareil_id}")
def modifier_inventaire(appareil_id: str, item: MetadonneesAppareil, utilisateur: dict = Depends(require_admin)):
    try:
        service.obtenir(appareil_id)
    except Exception as erreur:
        raise HTTPException(status_code=404, detail="Appareil introuvable") from erreur
    return evolutions.enregistrer_inventaire(appareil_id, item.model_dump())


@router.patch("/appareils/{appareil_id}/piece")
def affecter_piece(appareil_id: str, item: AffectationPiece, utilisateur: dict = Depends(require_admin)):
    try:
        service.obtenir(appareil_id)
    except Exception as erreur:
        raise HTTPException(status_code=404, detail="Appareil introuvable") from erreur
    nom_piece = item.piece.strip()
    pieces = PiecesRepository(service.repository.db_path)
    pieces.initialiser()
    if not any(p["nom"].casefold() == nom_piece.casefold() for p in pieces.lister()):
        try:
            pieces.ajouter(nom_piece, "", "#365B78")
        except sqlite3.IntegrityError:
            pass
    with sqlite3.connect(service.repository.db_path) as db:
        db.execute("UPDATE appareils_domotiques SET piece=? WHERE id=?", (nom_piece,appareil_id))
    return service.obtenir(appareil_id)


def _valider_regle(item: RegleAvancee):
    if len(set(item.jours)) != len(item.jours) or any(j not in range(1,8) for j in item.jours):
        raise HTTPException(status_code=422, detail="Les jours doivent être uniques et compris entre 1 et 7")
    if bool(item.heure_debut) != bool(item.heure_fin):
        raise HTTPException(status_code=422, detail="Les deux bornes horaires sont requises ensemble")
    for condition in item.conditions:
        try:
            appareil = service.obtenir(condition.appareil_id)
        except Exception as erreur:
            raise HTTPException(status_code=404, detail="Capteur introuvable") from erreur
        if appareil["type"] != "capteur":
            raise HTTPException(status_code=422, detail="Les conditions doivent utiliser des capteurs")
    for action in item.actions:
        try:
            appareil = service.obtenir(action.appareil_id)
        except Exception as erreur:
            raise HTTPException(status_code=404, detail="Appareil d'action introuvable") from erreur
        if "marche_arret" not in appareil["capacites"]:
            raise HTTPException(status_code=422, detail="L'appareil sélectionné ne prend pas en charge marche/arrêt")


@router.get("/automatisations/avancees")
def lister_regles(utilisateur: dict = Depends(get_current_user)):
    return evolutions.lister_regles()


@router.post("/automatisations/avancees", status_code=201)
def creer_regle(item: RegleAvancee, utilisateur: dict = Depends(require_admin)):
    _valider_regle(item)
    return evolutions.creer_regle({**item.model_dump(), "nom": item.nom.strip()})


@router.put("/automatisations/avancees/{identifiant}")
def modifier_regle(identifiant: str, item: RegleAvancee, utilisateur: dict = Depends(require_admin)):
    _valider_regle(item)
    resultat = evolutions.modifier_regle(identifiant, {**item.model_dump(), "nom": item.nom.strip()})
    if resultat is None:
        raise HTTPException(status_code=404, detail="Automatisation introuvable")
    return resultat


@router.patch("/automatisations/avancees/{identifiant}")
def activer_regle(identifiant: str, item: ActivationRegle, utilisateur: dict = Depends(require_admin)):
    resultat = evolutions.activer_regle(identifiant, item.active)
    if resultat is None:
        raise HTTPException(status_code=404, detail="Automatisation introuvable")
    return resultat


@router.delete("/automatisations/avancees/{identifiant}", status_code=204)
def supprimer_regle(identifiant: str, utilisateur: dict = Depends(require_admin)):
    from fastapi import Response
    if not evolutions.supprimer_regle(identifiant):
        raise HTTPException(status_code=404, detail="Automatisation introuvable")
    return Response(status_code=204)
