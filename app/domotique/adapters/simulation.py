from app.domotique.adapters.base import AdaptateurAppareil


class AdaptateurSimulation(AdaptateurAppareil):
    """Simule les commandes sans communiquer avec du matériel réel."""

    def appliquer_etat(self, appareil_id: str, allume: bool) -> bool:
        del appareil_id  # Identifiant conservé dans l'interface pour les futurs pilotes.
        return allume

    def appliquer_luminosite(self, appareil_id: str, luminosite: int) -> int:
        del appareil_id
        return luminosite

    def appliquer_temperature_couleur(self, appareil_id: str, temperature_couleur: int) -> int:
        del appareil_id
        return temperature_couleur
