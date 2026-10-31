import sqlite3

from app.domotique.adapters.base import AdaptateurAppareil
from app.domotique.models import capacites_pour_type
from app.domotique.repository import AppareilRepository
from app.domotique.evolutions import evolutions


class AppareilIntrouvable(Exception):
    pass


class TypeAppareilInvalide(Exception):
    pass


class CommandeNonSupportee(Exception):
    pass


class ErreurAdaptateur(Exception):
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
        try:
            etat_confirme = self.adaptateur.appliquer_etat(appareil_id, allume)
        except Exception as erreur:
            raise ErreurAdaptateur("Le pilote n’a pas pu appliquer la commande") from erreur
        resultat = self.repository.definir_etat(appareil_id, etat_confirme)
        if resultat is None:
            raise AppareilIntrouvable
        evolutions.enregistrer(appareil_id, "activation_lumiere" if allume else "extinction_lumiere", 1 if allume else 0, "etat")
        return self.presenter(resultat)

    def regler_luminosite(self, appareil_id: str, luminosite: int) -> dict:
        appareil = self.repository.obtenir(appareil_id)
        if appareil is None:
            raise AppareilIntrouvable
        if "luminosite" not in capacites_pour_type(appareil["type"]):
            raise CommandeNonSupportee
        if not 0 <= luminosite <= 100:
            raise ValueError("La luminosité doit être comprise entre 0 et 100")
        try:
            valeur_confirmee = self.adaptateur.appliquer_luminosite(appareil_id, luminosite)
        except Exception as erreur:
            raise ErreurAdaptateur("Le pilote n’a pas pu appliquer la luminosité") from erreur
        if not 0 <= valeur_confirmee <= 100:
            raise ErreurAdaptateur("Le pilote a retourné une luminosité invalide")
        resultat = self.repository.definir_luminosite(appareil_id, valeur_confirmee)
        if resultat is None:
            raise AppareilIntrouvable
        return self.presenter(resultat)

    def regler_temperature_couleur(self, appareil_id: str, temperature_couleur: int) -> dict:
        appareil = self.repository.obtenir(appareil_id)
        if appareil is None:
            raise AppareilIntrouvable
        if "temperature_couleur" not in capacites_pour_type(appareil["type"]):
            raise CommandeNonSupportee
        if not 2700 <= temperature_couleur <= 6500:
            raise ValueError("La température de couleur doit être comprise entre 2700 et 6500 K")
        try:
            valeur_confirmee = self.adaptateur.appliquer_temperature_couleur(appareil_id, temperature_couleur)
        except Exception as erreur:
            raise ErreurAdaptateur("Le pilote n’a pas pu appliquer la température de couleur") from erreur
        if not 2700 <= valeur_confirmee <= 6500:
            raise ErreurAdaptateur("Le pilote a retourné une température de couleur invalide")
        resultat = self.repository.definir_temperature_couleur(appareil_id, valeur_confirmee)
        if resultat is None:
            raise AppareilIntrouvable
        evolutions.enregistrer(appareil_id, "temperature_couleur", valeur_confirmee, "K")
        return self.presenter(resultat)

    def regler_couleur(self, appareil_id: str, couleur: str) -> dict:
        appareil = self.repository.obtenir(appareil_id)
        if appareil is None:
            raise AppareilIntrouvable
        if "couleur" not in capacites_pour_type(appareil["type"]):
            raise CommandeNonSupportee
        if not isinstance(couleur, str) or len(couleur) != 7 or couleur[0] != "#" or any(c not in "0123456789abcdefABCDEF" for c in couleur[1:]):
            raise ValueError("La couleur doit être au format hexadécimal #RRGGBB")
        couleur = couleur.upper()
        try:
            valeur_confirmee = self.adaptateur.appliquer_couleur(appareil_id, couleur)
        except Exception as erreur:
            raise ErreurAdaptateur("Le pilote n’a pas pu appliquer la couleur") from erreur
        if not isinstance(valeur_confirmee, str) or len(valeur_confirmee) != 7 or valeur_confirmee[0] != "#" or any(c not in "0123456789ABCDEFabcdef" for c in valeur_confirmee[1:]):
            raise ErreurAdaptateur("Le pilote a retourné une couleur invalide")
        resultat = self.repository.definir_couleur(appareil_id, valeur_confirmee.upper())
        if resultat is None:
            raise AppareilIntrouvable
        return self.presenter(resultat)


    def appliquer_scene(self, scene_id: str, piece: str | None = None) -> list[dict]:
        scene = self.repository.obtenir_scene(scene_id)
        if scene is None:
            raise AppareilIntrouvable
        lumieres = self.repository.lister(piece=piece, type_appareil="lumiere")
        if not lumieres:
            raise CommandeNonSupportee
        appareils_mis_a_jour = []
        for lumiere in lumieres:
            self.regler_luminosite(lumiere["id"], scene["luminosite"])
            self.regler_temperature_couleur(lumiere["id"], scene["temperature_couleur"])
            appareils_mis_a_jour.append(self.regler_couleur(lumiere["id"], scene["couleur"]))
        return appareils_mis_a_jour
