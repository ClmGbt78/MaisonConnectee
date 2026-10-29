
from fastapi import APIRouter, Depends, HTTPException
from app.core.security import get_current_user
import subprocess
from pathlib import Path

router = APIRouter(prefix="/rgb", tags=["RGB"])

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LIQUIDCTL = PROJECT_ROOT / ".venv" / "Scripts" / "liquidctl.exe"

# Uniquement les effets que nous avons testés avec succès.
MODES_AUTORISES = {
    "rainbow",
    "red_pulse",
    "spectrum_cycle",
    "spectrum_cycle_breathing",
}


@router.get("/modes")
def get_modes():
    return {"modes": sorted(MODES_AUTORISES)}


@router.post("/mode/{mode}")
def set_mode(
    mode: str,
    utilisateur_connecte: dict = Depends(get_current_user),
):
    if mode not in MODES_AUTORISES:
        raise HTTPException(status_code=400, detail="Mode RGB non autorisé")

    if not LIQUIDCTL.exists():
        raise HTTPException(
            status_code=500,
            detail="liquidctl.exe introuvable",
        )

    try:
        result = subprocess.run(
            [
                str(LIQUIDCTL),
                "set",
                "led3",
                "color",
                mode,
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
            cwd=str(PROJECT_ROOT),
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=504,
            detail="La commande RGB a dépassé le délai autorisé",
        )

    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=result.stderr.strip() or "Échec de la commande RGB",
        )

    return {"success": True, "mode": mode}
