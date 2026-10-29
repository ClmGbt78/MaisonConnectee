from typing import Protocol


class AdaptateurAppareil(Protocol):
    def appliquer_etat(self, appareil_id: str, allume: bool) -> bool:
        """Applique une commande et retourne l'état confirmé par l'adaptateur."""
        ...
