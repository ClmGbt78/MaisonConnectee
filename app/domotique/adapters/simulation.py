from app.domotique.adapters.base import AdaptateurAppareil


class AdaptateurSimulation(AdaptateurAppareil):
    """Simule les commandes sans communiquer avec du matériel réel."""

    def appliquer_etat(self, appareil_id: str, allume: bool) -> bool:
        del appareil_id  # Identifiant conservé dans l'interface pour les futurs pilotes.
        return allume
