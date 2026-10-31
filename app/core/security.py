import sqlite3

import jwt
from fastapi import Depends, Header, HTTPException

from app.core.config import get_settings

JWT_ISSUER = "maison-connectee"
JWT_AUDIENCE = "maison-connectee-frontend"
DB_PATH = get_settings().accounts_db_file


def get_jwt_secret() -> str:
    """Retourne le secret JWT après validation minimale de sa configuration."""
    secret = get_settings().jwt_secret.strip()
    if len(secret) < 32 or secret == "replace-with-a-random-secret-before-starting":
        raise RuntimeError(
            "JWT_SECRET doit contenir au moins 32 caractères aléatoires. "
            "Configure cette valeur dans le fichier .env ou l'environnement."
        )
    return secret


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
            get_jwt_secret(),
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
