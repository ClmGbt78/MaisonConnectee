import sqlite3
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from fastapi import APIRouter, HTTPException, Request
from app.core.security import JWT_AUDIENCE, JWT_ISSUER, JWT_SECRET
from app.core.config import get_settings
from pydantic import BaseModel, EmailStr, Field
from pwdlib import PasswordHash

router = APIRouter(prefix="/comptes", tags=["Comptes"])

BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "comptes.db"

password_hash = PasswordHash.recommended()
HASH_MOT_DE_PASSE_INVALIDE = password_hash.hash("invalid-password-placeholder")

# Limitation en mémoire : convient au mode local mono-processus. Pour plusieurs
# workers ou plusieurs serveurs, utiliser un stockage partagé (ex. Redis).
FENETRE_CONNEXION_SECONDES = 15 * 60
MAX_ECHECS_CONNEXION = 5
_echecs_connexion: dict[str, deque[float]] = defaultdict(deque)
_verrou_connexion = threading.Lock()


def _nettoyer_echecs(cles: tuple[str, ...], maintenant: float) -> None:
    for cle in cles:
        echecs = _echecs_connexion[cle]
        while echecs and maintenant - echecs[0] >= FENETRE_CONNEXION_SECONDES:
            echecs.popleft()


def _verifier_limite_connexion(email: str, adresse_ip: str) -> None:
    maintenant = time.monotonic()
    cles = (f"email:{email}", f"ip:{adresse_ip}")
    with _verrou_connexion:
        _nettoyer_echecs(cles, maintenant)
        if any(len(_echecs_connexion[cle]) >= MAX_ECHECS_CONNEXION for cle in cles):
            raise HTTPException(
                status_code=429,
                detail="Trop de tentatives de connexion. Réessaie dans 15 minutes.",
                headers={"Retry-After": str(FENETRE_CONNEXION_SECONDES)},
            )


def _enregistrer_echec_connexion(email: str, adresse_ip: str) -> None:
    maintenant = time.monotonic()
    with _verrou_connexion:
        cles = (f"email:{email}", f"ip:{adresse_ip}")
        _nettoyer_echecs(cles, maintenant)
        for cle in cles:
            _echecs_connexion[cle].append(maintenant)


def _reinitialiser_echecs_connexion(email: str, adresse_ip: str) -> None:
    with _verrou_connexion:
        _echecs_connexion.pop(f"email:{email}", None)
        _echecs_connexion.pop(f"ip:{adresse_ip}", None)


def initialiser_base():
    with sqlite3.connect(DB_PATH) as connexion:
        connexion.execute(
            """
            CREATE TABLE IF NOT EXISTS utilisateurs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                mot_de_passe_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'membre',
                actif INTEGER NOT NULL DEFAULT 1,
                date_creation TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


class Inscription(BaseModel):
    nom: str = Field(min_length=2, max_length=80)
    email: EmailStr
    mot_de_passe: str = Field(min_length=12, max_length=128)


class Connexion(BaseModel):
    email: EmailStr
    mot_de_passe: str = Field(min_length=1, max_length=128)


@router.post("/inscription")
def inscrire_utilisateur(utilisateur: Inscription):
    if not get_settings().allow_public_registration:
        raise HTTPException(
            status_code=403,
            detail="Les inscriptions publiques sont désactivées.",
        )

    nom = utilisateur.nom.strip()
    email = str(utilisateur.email).strip().lower()

    if len(nom) < 2:
        raise HTTPException(status_code=400, detail="Le nom est trop court")

    hash_mot_de_passe = password_hash.hash(utilisateur.mot_de_passe)

    try:
        with sqlite3.connect(DB_PATH) as connexion:
            curseur = connexion.execute(
                """
                INSERT INTO utilisateurs
                    (nom, email, mot_de_passe_hash)
                VALUES (?, ?, ?)
                """,
                (nom, email, hash_mot_de_passe),
            )
            utilisateur_id = curseur.lastrowid
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="Cette adresse e-mail possède déjà un compte",
        )

    return {
        "id": utilisateur_id,
        "nom": nom,
        "email": email,
        "role": "membre",
        "actif": True,
    }


@router.post("/connexion")
def connecter_utilisateur(donnees: Connexion, request: Request):
    email = str(donnees.email).strip().lower()
    adresse_ip = request.client.host if request.client else "inconnue"
    _verifier_limite_connexion(email, adresse_ip)

    with sqlite3.connect(DB_PATH) as connexion:
        connexion.row_factory = sqlite3.Row
        utilisateur = connexion.execute(
            """
            SELECT id, nom, email, mot_de_passe_hash, role, actif
            FROM utilisateurs
            WHERE email = ? COLLATE NOCASE
            """,
            (email,),
        ).fetchone()

    mot_de_passe_valide = password_hash.verify(
        donnees.mot_de_passe,
        (
            utilisateur["mot_de_passe_hash"]
            if utilisateur is not None
            else HASH_MOT_DE_PASSE_INVALIDE
        ),
    )

    if utilisateur is None or not mot_de_passe_valide or not utilisateur["actif"]:
        _enregistrer_echec_connexion(email, adresse_ip)
        raise HTTPException(
            status_code=401,
            detail="E-mail ou mot de passe incorrect",
        )

    _reinitialiser_echecs_connexion(email, adresse_ip)
    maintenant = datetime.now(timezone.utc)
    expiration = maintenant + timedelta(hours=8)

    jeton = jwt.encode(
        {
            "sub": str(utilisateur["id"]),
            "role": utilisateur["role"],
            "iat": maintenant,
            "exp": expiration,
            "iss": JWT_ISSUER,
            "aud": JWT_AUDIENCE,
        },
        JWT_SECRET,
        algorithm="HS256",
    )

    return {
        "access_token": jeton,
        "token_type": "bearer",
        "expires_in": 28800,
        "utilisateur": {
            "id": utilisateur["id"],
            "nom": utilisateur["nom"],
            "email": utilisateur["email"],
            "role": utilisateur["role"],
        },
    }
