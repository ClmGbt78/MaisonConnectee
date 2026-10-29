import shutil
from datetime import datetime, timezone

import psutil
from fastapi import APIRouter
import sqlite3
from pathlib import Path

router = APIRouter()

# Base de données située à la racine du projet
BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "systeme_historique.db"

def initialiser_base():
    with sqlite3.connect(DB_PATH) as connexion:
        connexion.execute("""
            CREATE TABLE IF NOT EXISTS historique_systeme (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                heure_utc TEXT NOT NULL,
                cpu_pct REAL NOT NULL,
                ram_pct REAL NOT NULL,
                disque_pct REAL NOT NULL
            )
        """)

initialiser_base()

@router.get("/")
def accueil():
    return {
        "projet": "Maison Connectée",
        "etat": "en fonctionnement",
    }


@router.get("/systeme")
def etat_systeme():
    return {
        "centrale": "PC Windows - développement",
        "heure_utc": datetime.now(timezone.utc).isoformat(),
        "modules": {
            "domotique": "en développement",
            "intelligence_artificielle": "non configurée",
            "rgb": "non configuré",
        },
    }


@router.get("/systeme/indicateurs")
def indicateurs_systeme():
    memoire = psutil.virtual_memory()
    disque = shutil.disk_usage("C:\\")

    cpu_pct = psutil.cpu_percent(interval=0.5)
    ram_pct = memoire.percent
    disque_pct = round(disque.used / disque.total * 100, 1)
    heure = datetime.now(timezone.utc).isoformat()

    # Enregistrer un relevé pour l'historique
    with sqlite3.connect(DB_PATH) as connexion:
        connexion.execute("""
        INSERT INTO historique_systeme
        (heure_utc, cpu_pct, ram_pct, disque_pct)
        VALUES (?, ?, ?, ?)
    """, (heure, cpu_pct, ram_pct, disque_pct))

    return {
        "cpu": {
            "utilisation_pct": cpu_pct,
        },
        "ram": {
            "utilisation_pct": ram_pct,
            "utilisee_gb": round(
                (memoire.total - memoire.available) / (1024 ** 3), 2
            ),
            "totale_gb": round(memoire.total / (1024 ** 3), 2),
        },
        "disque": {
            "utilisation_pct": disque_pct,
            "utilise_gb": round(disque.used / (1024 ** 3), 2),
            "libre_gb": round(disque.free / (1024 ** 3), 2),
            "total_gb": round(disque.total / (1024 ** 3), 2),
        },
        "heure_utc": heure,
    }

@router.get("/systeme/historique")
def obtenir_historique_systeme():
    with sqlite3.connect(DB_PATH) as connexion:
        connexion.row_factory = sqlite3.Row

        lignes = connexion.execute("""
            SELECT heure_utc, cpu_pct, ram_pct, disque_pct
            FROM historique_systeme
            ORDER BY id ASC
        """).fetchall()

    return [dict(ligne) for ligne in lignes]