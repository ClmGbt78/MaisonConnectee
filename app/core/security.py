import os
import sqlite3
from pathlib import Path

import jwt
from dotenv import load_dotenv
from fastapi import Depends, Header, HTTPException

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET est absent du fichier .env")

JWT_ISSUER = "maison-connectee"
JWT_AUDIENCE = "maison-connectee-frontend"
DB_PATH = BASE_DIR / "comptes.db"


def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    """Vérifie le JWT et confirme que le compte existe toujours et est actif."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=401,
            detail="Authentification requise",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization[7:].strip()
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Jeton manquant",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=["HS256"],
            issuer=JWT_ISSUER,
            audience=JWT_AUDIENCE,
            options={"require": ["exp", "sub", "iss", "aud"]},
        )
        utilisateur_id = int(payload["sub"])
    except (jwt.InvalidTokenError, TypeError, ValueError, KeyError):
        raise HTTPException(
            status_code=401,
            detail="Jeton invalide ou expiré",
            headers={"WWW-Authenticate": "Bearer"},
        )

    with sqlite3.connect(DB_PATH) as connexion:
        connexion.row_factory = sqlite3.Row
        utilisateur = connexion.execute(
            """
            SELECT id, nom, email, role, actif
            FROM utilisateurs
            WHERE id = ?
            """,
            (utilisateur_id,),
        ).fetchone()

    if utilisateur is None or not utilisateur["actif"]:
        raise HTTPException(
            status_code=401,
            detail="Compte inexistant ou désactivé",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return dict(utilisateur)


def require_admin(utilisateur: dict = Depends(get_current_user)):
    """Refuse les opérations d'administration aux comptes non administrateurs."""
    if str(utilisateur.get("role", "")).lower() != "admin":
        raise HTTPException(status_code=403, detail="Droits administrateur requis")
    return utilisateur
