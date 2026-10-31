import json
import sqlite3
from datetime import datetime, timedelta
from uuid import uuid4

from app.domotique.repository import DB_PATH


class EvolutionRepository:
    """Stockage additif de l'historique, des métadonnées et des règles avancées."""

    def __init__(self, db_path=DB_PATH):
        self.db_path = str(db_path)

    def initialiser(self):
        with sqlite3.connect(self.db_path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS historique_domotique (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                appareil_id TEXT NOT NULL,
                type_evenement TEXT NOT NULL,
                valeur REAL,
                unite TEXT,
                date_evenement TEXT NOT NULL
            )""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_historique_date ON historique_domotique(date_evenement)")
            db.execute("""CREATE TABLE IF NOT EXISTS inventaire_appareils (
                appareil_id TEXT PRIMARY KEY,
                fabricant TEXT,
                modele TEXT,
                reference_technique TEXT,
                protocole TEXT,
                adresse_materielle TEXT,
                notes TEXT,
                etat_connexion TEXT NOT NULL DEFAULT 'simulation',
                derniere_communication TEXT
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS automatisations_avancees (
                id TEXT PRIMARY KEY,
                nom TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                logique TEXT NOT NULL DEFAULT 'ET',
                conditions TEXT NOT NULL,
                actions TEXT NOT NULL,
                heure_debut TEXT,
                heure_fin TEXT,
                jours TEXT NOT NULL DEFAULT '[1,2,3,4,5,6,7]',
                derniere_execution TEXT
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS actions_differees (
                id TEXT PRIMARY KEY,
                automatisation_id TEXT NOT NULL,
                appareil_id TEXT NOT NULL,
                allume INTEGER NOT NULL,
                echeance TEXT NOT NULL,
                executee INTEGER NOT NULL DEFAULT 0
            )""")

    def enregistrer(self, appareil_id, evenement, valeur=None, unite=None, date=None):
        with sqlite3.connect(self.db_path) as db:
            db.execute(
                "INSERT INTO historique_domotique (appareil_id,type_evenement,valeur,unite,date_evenement) VALUES (?,?,?,?,?)",
                (appareil_id, evenement, valeur, unite, (date or datetime.now()).isoformat(timespec="seconds")),
            )

    def historique(self, appareil_id=None, evenement=None, depuis=None, limite=2000):
        requete = """SELECT h.id,h.appareil_id,h.type_evenement,h.valeur,h.unite,h.date_evenement,
                     a.nom AS appareil_nom,a.piece,a.type AS appareil_type
                     FROM historique_domotique h LEFT JOIN appareils_domotiques a ON a.id=h.appareil_id"""
        filtres, params = [], []
        if appareil_id:
            filtres.append("h.appareil_id=?"); params.append(appareil_id)
        if evenement:
            filtres.append("h.type_evenement=?"); params.append(evenement)
        if depuis:
            filtres.append("h.date_evenement>=?"); params.append(depuis)
        if filtres:
            requete += " WHERE " + " AND ".join(filtres)
        requete += " ORDER BY h.date_evenement DESC LIMIT ?"
        params.append(max(1, min(int(limite), 5000)))
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            return [dict(row) for row in db.execute(requete, params).fetchall()]

    def inventaire(self, appareils):
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            meta = {row["appareil_id"]: dict(row) for row in db.execute("SELECT * FROM inventaire_appareils")}
        resultat = []
        for appareil in appareils:
            info = meta.get(appareil["id"], {})
            resultat.append({**appareil, **{k: v for k, v in info.items() if k != "appareil_id"},
                "etat_connexion": info.get("etat_connexion", "simulation"),
                "informations_techniques": {
                    "type": appareil["type"], "capacites": appareil.get("capacites", []),
                    "fabricant": info.get("fabricant"), "modele": info.get("modele"),
                    "reference_technique": info.get("reference_technique"),
                    "protocole": info.get("protocole"), "adresse_materielle": info.get("adresse_materielle"),
                }})
        return resultat

    def enregistrer_inventaire(self, appareil_id, item):
        with sqlite3.connect(self.db_path) as db:
            db.execute("""INSERT INTO inventaire_appareils
                (appareil_id,fabricant,modele,reference_technique,protocole,adresse_materielle,notes,etat_connexion)
                VALUES (?,?,?,?,?,?,?,'simulation')
                ON CONFLICT(appareil_id) DO UPDATE SET fabricant=excluded.fabricant,modele=excluded.modele,
                reference_technique=excluded.reference_technique,protocole=excluded.protocole,
                adresse_materielle=excluded.adresse_materielle,notes=excluded.notes""",
                (appareil_id,item.get("fabricant"),item.get("modele"),item.get("reference_technique"),
                 item.get("protocole"),item.get("adresse_materielle"),item.get("notes")))
        return self.obtenir_inventaire(appareil_id)

    def obtenir_inventaire(self, appareil_id):
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            row = db.execute("SELECT * FROM inventaire_appareils WHERE appareil_id=?", (appareil_id,)).fetchone()
        return dict(row) if row else None

    def creer_regle(self, item):
        identifiant = str(uuid4())
        with sqlite3.connect(self.db_path) as db:
            db.execute("""INSERT INTO automatisations_avancees
                (id,nom,logique,conditions,actions,heure_debut,heure_fin,jours)
                VALUES (?,?,?,?,?,?,?,?)""",
                (identifiant,item["nom"],item["logique"],json.dumps(item["conditions"]),
                 json.dumps(item["actions"]),item.get("heure_debut"),item.get("heure_fin"),
                 json.dumps(item["jours"])))
        return self.obtenir_regle(identifiant)

    def lister_regles(self):
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute("SELECT * FROM automatisations_avancees ORDER BY nom COLLATE NOCASE").fetchall()
        return [self._convertir_regle(row) for row in rows]

    @staticmethod
    def _convertir_regle(row):
        item = dict(row)
        item["active"] = bool(item["active"])
        item["conditions"] = json.loads(item["conditions"])
        item["actions"] = json.loads(item["actions"])
        item["jours"] = json.loads(item["jours"])
        return item

    def obtenir_regle(self, identifiant):
        return next((r for r in self.lister_regles() if r["id"] == identifiant), None)

    def modifier_regle(self, identifiant, item):
        with sqlite3.connect(self.db_path) as db:
            cur = db.execute("""UPDATE automatisations_avancees SET nom=?,logique=?,conditions=?,actions=?,
                heure_debut=?,heure_fin=?,jours=? WHERE id=?""",
                (item["nom"],item["logique"],json.dumps(item["conditions"]),json.dumps(item["actions"]),
                 item.get("heure_debut"),item.get("heure_fin"),json.dumps(item["jours"]),identifiant))
        return self.obtenir_regle(identifiant) if cur.rowcount else None

    def activer_regle(self, identifiant, active):
        with sqlite3.connect(self.db_path) as db:
            cur = db.execute("UPDATE automatisations_avancees SET active=? WHERE id=?", (int(active),identifiant))
        return self.obtenir_regle(identifiant) if cur.rowcount else None

    def supprimer_regle(self, identifiant):
        with sqlite3.connect(self.db_path) as db:
            db.execute("DELETE FROM actions_differees WHERE automatisation_id=?", (identifiant,))
            cur = db.execute("DELETE FROM automatisations_avancees WHERE id=?", (identifiant,))
        return cur.rowcount > 0

    def executer_regles(self, service, maintenant=None):
        maintenant = maintenant or datetime.now()
        jour = maintenant.isoweekday()
        heure = maintenant.strftime("%H:%M")
        for regle in self.lister_regles():
            if not regle["active"] or jour not in regle["jours"]:
                continue
            if regle["derniere_execution"] == maintenant.date().isoformat():
                continue
            if regle["heure_debut"] and regle["heure_fin"]:
                debut, fin = regle["heure_debut"], regle["heure_fin"]
                dans_plage = debut <= heure <= fin if debut <= fin else (heure >= debut or heure <= fin)
                if not dans_plage:
                    continue
            evaluations = []
            for condition in regle["conditions"]:
                mesure = None
                try:
                    with sqlite3.connect(self.db_path) as db:
                        db.row_factory = sqlite3.Row
                        row = db.execute("SELECT valeur,type_mesure,mise_a_jour FROM mesures_capteurs WHERE appareil_id=?",
                                         (condition["appareil_id"],)).fetchone()
                    mesure = dict(row) if row else None
                except (KeyError, sqlite3.Error):
                    mesure = None
                if not mesure:
                    evaluations.append(False); continue
                valeur = float(mesure["valeur"])
                operateur, seuil = condition["operateur"], float(condition["seuil"])
                evaluations.append({"<":valeur < seuil,"<=":valeur <= seuil,">":valeur > seuil,
                                    ">=":valeur >= seuil,"=":valeur == seuil,"!=":valeur != seuil}.get(operateur,False))
            valide = all(evaluations) if regle["logique"] == "ET" else any(evaluations)
            if not valide:
                continue
            for action in regle["actions"]:
                delai = int(action.get("delai_secondes",0))
                if delai:
                    echeance = maintenant + timedelta(seconds=delai)
                    with sqlite3.connect(self.db_path) as db:
                        db.execute("INSERT INTO actions_differees VALUES (?,?,?,?,?,0)",
                            (str(uuid4()),regle["id"],action["appareil_id"],int(action["allume"]),echeance.isoformat(timespec="seconds")))
                else:
                    service.commander(action["appareil_id"],bool(action["allume"]))
            with sqlite3.connect(self.db_path) as db:
                db.execute("UPDATE automatisations_avancees SET derniere_execution=? WHERE id=?",
                           (maintenant.date().isoformat(),regle["id"]))
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            dus = db.execute("SELECT * FROM actions_differees WHERE executee=0 AND echeance<=?",
                             (maintenant.isoformat(timespec="seconds"),)).fetchall()
        for action in dus:
            try:
                service.commander(action["appareil_id"],bool(action["allume"]))
            finally:
                with sqlite3.connect(self.db_path) as db:
                    db.execute("UPDATE actions_differees SET executee=1 WHERE id=?", (action["id"],))


evolutions = EvolutionRepository()
evolutions.initialiser()
