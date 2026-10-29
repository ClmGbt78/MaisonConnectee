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
