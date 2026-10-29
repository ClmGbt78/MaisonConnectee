import sqlite3
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from app.core.security import get_current_user
from pydantic import BaseModel

router = APIRouter(
    prefix="/domotique",
    tags=["Domotique"],
)

BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "systeme_historique.db"


def initialiser_base_domotique():
    with sqlite3.connect(DB_PATH) as connexion:
        connexion.execute("""
            CREATE TABLE IF NOT EXISTS appareils_domotiques (
                id TEXT PRIMARY KEY,
                nom TEXT NOT NULL,
                piece TEXT NOT NULL,
                type TEXT NOT NULL,
                allume INTEGER NOT NULL DEFAULT 0
            )
        """)

        appareils_initiaux = [
            ("lampe-salon", "Lampe du salon", "Salon", "lumiere", 0),
            ("ventilateur", "Ventilateur", "Chambre", "ventilation", 0),
            ("prise-bureau", "Prise du bureau", "Bureau", "prise", 0),
        ]

        connexion.executemany("""
            INSERT OR IGNORE INTO appareils_domotiques
                (id, nom, piece, type, allume)
            VALUES (?, ?, ?, ?, ?)
        """, appareils_initiaux)


initialiser_base_domotique()


class CommandeAppareil(BaseModel):
    allume: bool

class NouvelAppareil(BaseModel):
    id: str
    nom: str
    piece: str
    type: str

def convertir_appareil(ligne):
    appareil = dict(ligne)
    appareil["allume"] = bool(appareil["allume"])
    return appareil

@router.get("/appareils")
def obtenir_appareils():
    with sqlite3.connect(DB_PATH) as connexion:
        connexion.row_factory = sqlite3.Row

        lignes = connexion.execute("""
            SELECT id, nom, piece, type, allume
            FROM appareils_domotiques
            ORDER BY id
        """).fetchall()

    return [convertir_appareil(ligne) for ligne in lignes]


@router.post("/appareils", status_code=201)
def ajouter_appareil(
    nouvel_appareil: NouvelAppareil,
    utilisateur_connecte: dict = Depends(get_current_user),
):
    appareil_id = nouvel_appareil.id.strip()
    nom = nouvel_appareil.nom.strip()
    piece = nouvel_appareil.piece.strip()
    type_appareil = nouvel_appareil.type.strip().lower()

    if not appareil_id or not nom or not piece:
        raise HTTPException(
            status_code=422,
            detail="L'identifiant, le nom et la pièce sont obligatoires",
        )

    types_autorises = {"lumiere", "ventilation", "prise", "capteur"}

    if type_appareil not in types_autorises:
        raise HTTPException(
            status_code=422,
            detail="Type invalide. Types autorisés : lumiere, ventilation, prise, capteur",
        )

    try:
        with sqlite3.connect(DB_PATH) as connexion:
            connexion.execute("""
                INSERT INTO appareils_domotiques
                    (id, nom, piece, type, allume)
                VALUES (?, ?, ?, ?, 0)
            """, (appareil_id, nom, piece, type_appareil))
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="Un appareil avec cet identifiant existe déjà",
        )

    return {
        "id": appareil_id,
        "nom": nom,
        "piece": piece,
        "type": type_appareil,
        "allume": False,
    }

@router.delete("/appareils/{appareil_id}", status_code=204)
def supprimer_appareil(
    appareil_id: str,
    utilisateur_connecte: dict = Depends(get_current_user),
):
    with sqlite3.connect(DB_PATH) as connexion:
        curseur = connexion.execute("""
            DELETE FROM appareils_domotiques
            WHERE id = ?
        """, (appareil_id,))

        if curseur.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Appareil introuvable",
            )

    return

@router.get("/appareils/{appareil_id}")
def obtenir_appareil(appareil_id: str):
    with sqlite3.connect(DB_PATH) as connexion:
        connexion.row_factory = sqlite3.Row

        ligne = connexion.execute("""
            SELECT id, nom, piece, type, allume
            FROM appareils_domotiques
            WHERE id = ?
        """, (appareil_id,)).fetchone()

    if ligne is None:
        raise HTTPException(
            status_code=404,
            detail="Appareil introuvable",
        )

    return convertir_appareil(ligne)


@router.patch("/appareils/{appareil_id}")
def modifier_appareil(
    appareil_id: str,
    commande: CommandeAppareil,
    utilisateur_connecte: dict = Depends(get_current_user),
):
    with sqlite3.connect(DB_PATH) as connexion:
        curseur = connexion.execute("""
            UPDATE appareils_domotiques
            SET allume = ?
            WHERE id = ?
        """, (int(commande.allume), appareil_id))

        if curseur.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Appareil introuvable",
            )

        connexion.row_factory = sqlite3.Row

        ligne = connexion.execute("""
            SELECT id, nom, piece, type, allume
            FROM appareils_domotiques
            WHERE id = ?
        """, (appareil_id,)).fetchone()

    return convertir_appareil(ligne)
