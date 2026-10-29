from typing import Protocol


class AdaptateurAppareil(Protocol):
    def appliquer_etat(self, appareil_id: str, allume: bool) -> bool:
        """Applique une commande et retourne l'état confirmé par l'adaptateur."""
        ...

    def appliquer_luminosite(self, appareil_id: str, luminosite: int) -> int:
        """Applique une luminosité (0-100) et retourne la valeur confirmée."""
        ...

    def appliquer_temperature_couleur(self, appareil_id: str, temperature_couleur: int) -> int:
        """Applique une température de couleur en kelvins (2700-6500)."""
        ...

    def appliquer_couleur(self, appareil_id: str, couleur: str) -> str:
        """Applique une couleur RGB au format #RRGGBB."""
        ...
