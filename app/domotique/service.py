import sqlite3

from app.domotique.adapters.base import AdaptateurAppareil
from app.domotique.models import capacites_pour_type
from app.domotique.repository import AppareilRepository


class AppareilIntrouvable(Exception):
    pass


class TypeAppareilInvalide(Exception):
    pass


class CommandeNonSupportee(Exception):
    pass


class AppareilService:
    def __init__(self, repository: AppareilRepository, adaptateur: AdaptateurAppareil):
        self.repository = repository
        self.adaptateur = adaptateur

    @staticmethod
    def presenter(appareil: dict) -> dict:
        appareil["capacites"] = capacites_pour_type(appareil["type"])
        return appareil

    def lister(self, piece: str | None = None, type_appareil: str | None = None) -> list[dict]:
        return [self.presenter(a) for a in self.repository.lister(piece, type_appareil)]

    def obtenir(self, appareil_id: str) -> dict:
        appareil = self.repository.obtenir(appareil_id)
        if appareil is None:
            raise AppareilIntrouvable
        return self.presenter(appareil)

    def ajouter(self, appareil: dict) -> dict:
        if appareil["type"] not in {"lumiere", "ventilation", "prise", "capteur"}:
            raise TypeAppareilInvalide
        try:
            resultat = self.repository.ajouter(appareil)
        except sqlite3.IntegrityError as erreur:
            raise ValueError("Un appareil avec cet identifiant existe déjà") from erreur
        return self.presenter(resultat)

    def supprimer(self, appareil_id: str) -> None:
        if not self.repository.supprimer(appareil_id):
            raise AppareilIntrouvable

    def commander(self, appareil_id: str, allume: bool) -> dict:
        appareil = self.repository.obtenir(appareil_id)
        if appareil is None:
            raise AppareilIntrouvable
        if "marche_arret" not in capacites_pour_type(appareil["type"]):
            raise CommandeNonSupportee
        # L'état n'est persisté qu'après confirmation de l'adaptateur.
        etat_confirme = self.adaptateur.appliquer_etat(appareil_id, allume)
        resultat = self.repository.definir_etat(appareil_id, etat_confirme)
        if resultat is None:
            raise AppareilIntrouvable
        return self.presenter(resultat)
