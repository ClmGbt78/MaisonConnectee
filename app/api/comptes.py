import sqlite3
from datetime import datetime, timedelta, timezone
import jwt

from pathlib import Path
from fastapi import APIRouter, HTTPException
from app.core.security import JWT_AUDIENCE, JWT_ISSUER, JWT_SECRET
from pydantic import BaseModel, EmailStr, Field
from pwdlib import PasswordHash

router = APIRouter(prefix="/comptes", tags=["Comptes"])

BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "comptes.db"

password_hash = PasswordHash.recommended()


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


initialiser_base()


class Inscription(BaseModel):
    nom: str = Field(min_length=2, max_length=80)
    email: EmailStr
    mot_de_passe: str = Field(min_length=12, max_length=128)

class Connexion(BaseModel):
    email: EmailStr
    mot_de_passe: str = Field(min_length=1, max_length=128)


@router.post("/inscription")
def inscrire_utilisateur(utilisateur: Inscription):
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
def connecter_utilisateur(donnees: Connexion):
    email = str(donnees.email).strip().lower()

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

    if (
        utilisateur is None
        or not password_hash.verify(
            donnees.mot_de_passe,
            utilisateur["mot_de_passe_hash"],
        )
        or not utilisateur["actif"]
    ):
        raise HTTPException(
            status_code=401,
            detail="E-mail ou mot de passe incorrect",
        )

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