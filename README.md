📋 Projet B3 IA & Data — Récap
🎯 Le sujet
LoL Win Predictor — Application de data storytelling qui prédit en temps réel le pourcentage de victoire d'une partie de League of Legends, avec affichage via une interface (Streamlit) qui poll la partie en cours et donne des conseils basés sur l'état du match.
Pourquoi ce sujet coche toutes les cases :

Multi-sources de données (Riot API + Live Client API)
Vrai problème ML (classification binaire win/loss)
Storytelling naturel (à quel moment une partie est-elle "perdue" statistiquement ?)
Démo qui marque (app live pendant la soutenance)
Sujet original (jury n'aura pas 5 projets identiques)

🧠 Concepts importants validés
LLM vs ML : un LLM est techniquement du ML (deep learning), mais la grille demande d'appliquer un modèle (Random Forest, XGBoost, K-means...). Consommer une API LLM ≠ appliquer du ML. Donc on fait du vrai ML supervisé classique (XGBoost / Logistic Regression).
Cohérence train/inference : les features utilisées pour entraîner le modèle doivent être exactement les mêmes que celles disponibles en live. D'où l'importance d'avoir testé la Live Client API en premier.
🔍 Tests effectués ce soir

Test PowerShell → galères avec TLS, certificats self-signed
Solution qui marche : curl.exe -k https://127.0.0.1:2999/liveclientdata/allgamedata
2 snapshots analysés (Practice Tool solo + Practice Tool avec mannequin)

✅ Découvertes Live Client API
L'endpoint https://127.0.0.1:2999/liveclientdata/allgamedata renvoie un JSON avec :
Sur le joueur actif (toi) :

Stats complètes (armor, AP, AD, magic resist, attack speed, penetration...)
Niveau, HP, mana, gold actuel
Runes complètes
Niveau de chaque sort (Q/W/E/R)

Sur tous les joueurs (allPlayers, array de 10 en 5v5) :

championName, team (ORDER = bleu, CHAOS = rouge)
level, position
scores : kills / deaths / assists / creepScore / wardScore
items équipés
⚠️ Filtrer les isBot=true (ils renvoient "error": "Unable to find player")

Section events : GameStart, MinionsSpawning, et en vraie partie : kills, tours détruites, dragons, hérauts, barons.
Important : le curl est une photo à l'instant T, pas un enregistrement. Pour suivre l'évolution = poller toutes les 5-10s (c'est ce que fera l'app finale).
🎯 Features finales (9 features)
Différentiels équipe bleue - rouge :

kills_diff
deaths_diff
cs_diff
level_diff (moyenne)
towers_diff
dragons_diff
heralds_diff
barons_diff

+ contexte :
9. game_time_minutes
Cible : blue_wins (0 ou 1)
🏗️ Architecture du projet
┌─────────────────────────────────────────────┐
│  PHASE 1 : ENTRAÎNEMENT (offline)           │
├─────────────────────────────────────────────┤
│  Riot API → matchs Master+ → timelines      │
│  → Snapshots à 10/15/20 min                 │
│  → Feature engineering                       │
│  → XGBoost + Logistic Regression (baseline) │
│  → Sauvegarde modèle .pkl                   │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  PHASE 2 : LIVE (pendant une partie)        │
├─────────────────────────────────────────────┤
│  Live Client API (localhost:2999)           │
│  → Polling toutes les 5-10 secondes         │
│  → Extraction features (mêmes que train)    │
│  → Prédiction via modèle chargé             │
│  → Conseils basés sur écarts médians        │
│  → Affichage Streamlit                       │
└─────────────────────────────────────────────┘
📅 Roadmap 5-7 jours effectifs (2 semaines calendrier)
JourTâchesJ1Setup repo Git, obtenir clé API Riot, valider Live Client API (✅ fait ce soir)J2Script de pull Riot API → 2000-5000 matchs Master+ avec timelines (lancer en background)J3Feature engineering, parsing timelines, EDA + viz storytellingJ4Modélisation : Logistic Regression baseline + XGBoost, comparaison, métriquesJ5App Streamlit : polling Live Client API + affichage prédiction + conseilsJ6Doc README, notebook propre, slides oralJ7Buffer pour imprévus (obligatoire)
📦 Livrables attendus (grille)

 Dépôt Git avec tout le code et la doc
 Jupyter Notebook qui retrace la démarche
 Application Streamlit déployée localement
 Documentation technique + manuel d'installation

⚠️ À ne PAS faire (économie de temps)

❌ Overlay transparent par-dessus le jeu (trop de friction)
❌ Calculer les stats détaillées des autres joueurs depuis leurs items
❌ Plusieurs modèles par timestamp (un seul avec timestamp en feature)
❌ Pull de 20k matchs (3-5k suffit largement)
❌ Système de conseils sophistiqué (3-5 règles simples suffisent)

🚀 Actions concrètes pour DEMAIN

Créer le repo GitHub (nom suggéré : lol-win-predictor ou lol-overlay-ml)
Récupérer ta clé API Riot : https://developer.riotgames.com/ (clé RGAPI-..., expire toutes les 24h, à régénérer chaque jour)
Me dire ta région cible (EUW recommandé) et ton IDE (VSCode, Cursor...) — questions que je t'ai posées et que t'as pas encore répondues
Ne PAS commit ta clé API sur GitHub (faire un .env + .gitignore dès le début)
Reviens ici quand t'es prêt, je te génère :

Structure complète du repo (arborescence + fichiers vides)
Premier script Python qui valide la connexion à la Riot API
Script de pull des matchs Master+ avec leurs timelines
