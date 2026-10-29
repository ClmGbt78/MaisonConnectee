from typing import Literal

from pydantic import BaseModel, Field

TypeAppareil = Literal["lumiere", "ventilation", "prise", "capteur"]


class Appareil(BaseModel):
    id: str
    nom: str
    piece: str
    type: TypeAppareil
    allume: bool
    luminosite: int | None = None
    capacites: list[str] = Field(default_factory=list)


def capacites_pour_type(type_appareil: str) -> list[str]:
    """Décrit les commandes actuellement prises en charge par chaque type."""
    if type_appareil == "lumiere":
        return ["marche_arret", "luminosite"]
    if type_appareil in {"ventilation", "prise"}:
        return ["marche_arret"]
    if type_appareil == "capteur":
        return ["lecture"]
    return []
