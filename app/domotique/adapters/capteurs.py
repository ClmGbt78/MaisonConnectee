from typing import Protocol

from app.domotique.automations import AutomatisationRepository


class AdaptateurCapteur(Protocol):
    """Contrat commun aux capteurs simulés et aux futurs capteurs physiques.

    La mesure retournée utilise les champs appareil_id, type_mesure, valeur
    et mise_a_jour (date ISO 8601). Retourner None si aucune mesure n'est disponible.
    """

    def lire_mesure(self, capteur_id: str) -> dict | None:
        ...


class AdaptateurCapteurSimulation:
    """Lit les dernières mesures injectées dans SQLite par l'interface de simulation."""

    def __init__(self, repository: AutomatisationRepository):
        self.repository = repository

    def lire_mesure(self, capteur_id: str) -> dict | None:
        return self.repository.mesure(capteur_id)
