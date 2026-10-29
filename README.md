# Maison Connectée

Projet personnel de centrale domotique et d'assistant intelligent.

## Objectifs

- Centraliser les équipements domotiques.
- Développer une API en Python avec FastAPI.
- Créer une interface web en JavaScript/TypeScript.
- Connecter des ESP32 et Arduino.
- Intégrer un assistant IA.
- Contrôler l'éclairage RGB du PC et du clavier.
- Prévoir un futur NAS.

## Environnement de développement

- Windows
- Python
- FastAPI
- Visual Studio Code
- Git

## Configuration locale

1. Copie `.env.example` vers `.env`.
2. Génère une clé JWT aléatoire et privée :
   ```powershell
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```
3. Remplace `JWT_SECRET` dans `.env` par cette valeur. Ne partage jamais ce secret et ne le committe pas.
4. L'inscription publique est désactivée par défaut. Pour une session de développement où elle est nécessaire, définis `ALLOW_PUBLIC_REGISTRATION=true` dans `.env`, puis redémarre le backend. Remets-la à `false` quand elle n'est plus nécessaire.

Ne réutilise pas la clé d'exemple en production. Ce projet reste destiné au développement local tant qu'une configuration de déploiement et de sécurité complète n'a pas été auditée.

## Authentification et rôles

- Les connexions sont limitées à 5 échecs par adresse e-mail ou adresse IP sur une fenêtre de 15 minutes. Une réponse HTTP 429 indique que la limite est atteinte.
- La limitation actuelle est conservée en mémoire et convient au développement local avec un seul processus. Elle est réinitialisée au redémarrage et ne remplace pas un limiteur partagé pour un déploiement multi-processus.
- Les comptes ont le rôle `membre` par défaut. Les membres peuvent consulter et piloter les appareils, mais seuls les comptes `admin` peuvent ajouter ou supprimer des appareils. Le backend vérifie ce droit ; masquer les boutons dans l'interface ne constitue pas une protection suffisante.
- Pour attribuer le rôle administrateur à un compte existant, exécute localement cette commande depuis la racine du projet, puis saisis l'adresse e-mail du compte à promouvoir :

  ```powershell
  python -c "import sqlite3; email=input('E-mail du compte à promouvoir en admin : ').strip().lower(); db=sqlite3.connect('comptes.db'); cur=db.execute('UPDATE utilisateurs SET role=? WHERE email=? COLLATE NOCASE', ('admin', email)); db.commit(); print('Rôle admin attribué.' if cur.rowcount else 'Compte introuvable.'); db.close()"
  ```

  Ne promeus que des comptes de confiance et ne partage pas le fichier `comptes.db`.

## Architecture domotique

La domotique est organisée en couches pour séparer l'API, les règles métier, le stockage et les pilotes :

- `app/api/domotique.py` : routes HTTP, authentification et traduction des erreurs en réponses API.
- `app/domotique/service.py` : règles métier et validation des commandes.
- `app/domotique/repository.py` : accès à SQLite.
- `app/domotique/adapters/` : interfaces des pilotes d'appareils et de capteurs, avec adaptateurs de simulation locaux.
- `app/domotique/models.py` : capacités exposées par type d'appareil.

L'adaptateur actuel est **une simulation** : aucune commande n'est envoyée à du matériel. Les capteurs sont en lecture seule. Les lumières exposent également les capacités `luminosite` (0 à 100), `temperature_couleur` (2700 à 6500 K) et `couleur` (format hexadécimal `#RRGGBB`). La luminosité se règle via `PATCH /api/domotique/appareils/{id}/luminosite` avec le corps `{"luminosite": 65}` ; la température de couleur via `PATCH /api/domotique/appareils/{id}/temperature-couleur` avec le corps `{"temperature_couleur": 3000}`. Ces valeurs sont persistées dans SQLite. La température basse correspond à une lumière plus chaude, la température élevée à une lumière plus froide. La couleur se règle via `PATCH /api/domotique/appareils/{id}/couleur` avec le corps `{"couleur": "#FF8800"}`. La couleur RGB est persistée dans SQLite. L’adaptateur reste une simulation et n’agit sur aucun matériel réel. Les nouvelles colonnes sont ajoutées par migration additive, sans écraser les réglages existants. Les lumières déjà présentes reçoivent la couleur blanche `#FFFFFF` uniquement si aucune couleur n'est enregistrée. Les réponses des appareils incluent le champ `capacites`, et la liste peut être filtrée avec `GET /api/domotique/appareils?piece=Salon&type=lumiere`.

### Données locales

La domotique continue d'utiliser `systeme_historique.db`. L'initialisation crée la table si nécessaire et ajoute les appareils de démonstration uniquement s'ils n'existent pas ; elle ne supprime pas les lignes ni ne réinitialise les états existants. `comptes.db` n'est pas modifiée par cette architecture.

Avant toute future évolution du schéma, fais une copie des bases locales. Ne supprime pas les fichiers SQLite pour résoudre un problème de démarrage.

### Tests

Les tests unitaires du dépôt et du service domotique utilisent une base SQLite temporaire :
```powershell
.\.venv\Scripts\python.exe -m pytest
```


## Scènes lumineuses

Les scènes permettent d'enregistrer des ambiances nommées et de les appliquer à toutes les lumières compatibles. Chaque scène contient une luminosité (0–100), une température de couleur (2700–6500 K) et une couleur RGB au format `#RRGGBB`.

Routes authentifiées :
- `GET /api/domotique/scenes` : lister les scènes.
- `POST /api/domotique/scenes` : créer une scène avec `nom`, `luminosite`, `temperature_couleur` et `couleur`.
- `DELETE /api/domotique/scenes/{scene_id}` : supprimer une scène.
- `POST /api/domotique/scenes/{scene_id}/appliquer` : appliquer les trois réglages à chaque lumière.

Les scènes sont enregistrées dans une table SQLite dédiée `scenes_lumineuses`. Leur création ou suppression ne modifie pas les enregistrements des appareils. L'application d'une scène pilote les lumières l'une après l'autre ; si un pilote échoue, l'API signale une erreur et certains réglages déjà appliqués peuvent nécessiter une vérification. L'adaptateur actuel est simulé et ne commande aucun matériel réel.


## Automatisations domotiques

Les automatisations horaires sont exécutées localement par le backend FastAPI (vérification toutes les 15 secondes, selon l'heure locale de l'ordinateur). Elles restent enregistrées dans SQLite après un redémarrage.

- Une règle associe une scène lumineuse, une heure, un ou plusieurs jours de la semaine et, facultativement, une pièce.
- Une extinction différée facultative peut être ajoutée après l'application de la scène (de 1 à 1440 minutes). Elle éteint les lumières de la pièce ciblée, ou toutes les lumières si aucune pièce n'est sélectionnée.
- Les règles peuvent être activées/désactivées ou supprimées depuis l'interface.
- Routes authentifiées : `GET/POST /api/domotique/automatisations`, `PATCH /api/domotique/automatisations/{id}` (corps `{"active": false}`) et `DELETE /api/domotique/automatisations/{id}`.

Le moteur utilise l'heure locale de Windows et fonctionne tant que le backend est démarré. Si le PC ou le backend est arrêté à l'heure prévue, la règle est exécutée au prochain démarrage si son créneau du jour est déjà passé ; une règle ne s'exécute qu'une fois par jour. L'extinction différée est conservée et sera traitée au prochain démarrage si son échéance est dépassée.

Le moteur est prévu pour l'exécution locale avec un seul processus FastAPI. Ne lance pas plusieurs workers Uvicorn, car chaque processus démarrerait son propre moteur. Les actions sont simulées par l'adaptateur actuel et n'envoient aucune commande à du matériel réel.


## Automatisations conditionnelles et capteurs simulés

Deux capteurs de démonstration sont ajoutés sans remplacer les appareils déjà présents : un capteur de luminosité et un détecteur de présence dans le salon.

- **Luminosité faible** : applique une scène lorsque la mesure passe sous un seuil (en pourcentage).
- **Présence détectée** : applique une scène lorsqu'une présence est signalée.
- **Absence prolongée** : éteint les lumières ciblées après la durée d'absence configurée.
- Les règles peuvent être activées, désactivées et supprimées. Un délai anti-répétition de cinq minutes évite les déclenchements en boucle.
- La simulation des capteurs est disponible via l'interface et les routes authentifiées :
  - `GET /api/domotique/automatisations/capteurs`
  - `PUT /api/domotique/automatisations/capteurs/{capteur_id}/mesure` avec `{"type_mesure":"luminosite","valeur":20}` ou `{"type_mesure":"presence","valeur":1}` (0 = absence).
  - `GET/POST /api/domotique/automatisations/conditionnelles`
  - `PATCH/DELETE /api/domotique/automatisations/conditionnelles/{id}`

Les mesures et règles sont conservées dans SQLite. Une première mesure du capteur doit être simulée avant de créer une règle, afin de vérifier que le type de mesure correspond au déclencheur. Le moteur lit désormais les mesures via le contrat `AdaptateurCapteur` (`lire_mesure`) ; `AdaptateurCapteurSimulation` fournit l'implémentation actuelle à partir de SQLite. Un futur pilote physique pourra implémenter ce même contrat sans modifier les règles métier. Les capteurs et actions restent simulés : aucun matériel réel n'est piloté. L'absence prolongée est calculée à partir de l'heure de la dernière mesure indiquant l'absence ; un redémarrage conserve cette date.

### Transport USB / série pour les futurs capteurs

Un transport série générique est disponible dans `app/domotique/adapters/transport_serie.py`. Il fournit une communication en octets avec un port tel que `COM3` sous Windows, sans imposer le protocole d'un capteur particulier.

- `ConfigurationPortSerie` configure le port, le débit (9600 bauds par défaut) et le délai de lecture.
- `TransportSeriePySerial` expose `ouvrir()`, `lire(taille)`, `ecrire(octets)` et `fermer()`, ainsi qu'une utilisation avec `with`.
- Le port série est injecté dans les tests : aucun matériel n'est nécessaire pour tester le transport.
- La dépendance matérielle reste facultative. Lorsqu'un capteur compatible sera choisi, installe pySerial dans l'environnement virtuel avec `python -m pip install pyserial`. Elle n'est pas ajoutée aux dépendances obligatoires du projet.
- Ce transport ne décode pas les messages et ne lit aucune mesure à lui seul. Un adaptateur propre au modèle du capteur devra convertir son protocole en mesures compatibles avec `AdaptateurCapteur`.

Aucun port COM n'est ouvert automatiquement au démarrage et aucun matériel n'est piloté tant qu'un adaptateur concret n'a pas été configuré.



### Découverte des ports USB / série

La route authentifiée `GET /api/domotique/automatisations/ports-serie` liste les ports série détectés sur le PC Windows. Elle retourne le nom du port, sa description, le fabricant et l'identifiant USB lorsqu'il est disponible.

Cette découverte est passive : elle n'ouvre aucun port, n'envoie aucune donnée et ne modifie pas les capteurs simulés. Si pySerial n'est pas installé, l'API répond avec le statut 503 et indique la commande d'installation. Pour activer cette fonctionnalité dans l'environnement virtuel :

```powershell
.\\.venv\\Scripts\\python.exe -m pip install pyserial
```

Un résultat vide signifie simplement qu'aucun port série n'a été détecté à cet instant.


### Association d'un capteur à un port série

Les routes authentifiées permettent d'enregistrer une association descriptive entre un capteur logique et un port COM détecté :

- `GET /api/domotique/automatisations/capteurs/configurations-serie` : lister les associations.
- `PUT /api/domotique/automatisations/capteurs/{capteur_id}/configuration-serie` avec `{"port":"COM4","debit":9600}` : associer un port détecté au capteur.
- `DELETE /api/domotique/automatisations/capteurs/{capteur_id}/configuration-serie` : retirer l'association.

Le port doit apparaître dans la découverte actuelle et ne peut être associé qu'à un seul capteur. Le débit est configurable (300 à 2 000 000 bauds, 9600 par défaut). La configuration est persistée dans SQLite. Cette étape ne réalise aucune connexion série, ne transmet aucun octet et ne modifie pas le mode de simulation. Le champ protocole reste « a_configurer » jusqu'à ce que le modèle de capteur et son format de message soient connus.
