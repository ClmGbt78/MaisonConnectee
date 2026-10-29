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
- `app/domotique/adapters/` : interface des pilotes et adaptateur de simulation local.
- `app/domotique/models.py` : capacités exposées par type d'appareil.

L'adaptateur actuel est **une simulation** : aucune commande n'est envoyée à du matériel. Les capteurs sont en lecture seule. Les lumières exposent également la capacité `luminosite` (0 à 100) via `PATCH /api/domotique/appareils/{id}/luminosite` avec le corps `{"luminosite": 65}`. Cette valeur est persistée dans SQLite ; l’adaptateur reste une simulation et n’agit sur aucun matériel réel. Les réponses des appareils incluent le champ `capacites`, et la liste peut être filtrée avec `GET /api/domotique/appareils?piece=Salon&type=lumiere`.

### Données locales

La domotique continue d'utiliser `systeme_historique.db`. L'initialisation crée la table si nécessaire et ajoute les appareils de démonstration uniquement s'ils n'existent pas ; elle ne supprime pas les lignes ni ne réinitialise les états existants. `comptes.db` n'est pas modifiée par cette architecture.

Avant toute future évolution du schéma, fais une copie des bases locales. Ne supprime pas les fichiers SQLite pour résoudre un problème de démarrage.

### Tests

Les tests unitaires du dépôt et du service domotique utilisent une base SQLite temporaire :
```powershell
.\.venv\Scripts\python.exe -m pytest
```
