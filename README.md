🎮 LoL Win Predictor

Prédiction en temps réel du taux de victoire d'une partie de League of Legends, avec interface live et conseils basés sur l'état du match.

Projet B3 IA & Data — Ynov Aix-en-Provence

📖 Présentation
Ce projet est une application de data storytelling qui exploite deux APIs Riot Games pour prédire, en temps réel pendant une partie de League of Legends, la probabilité de victoire de l'équipe bleue.
L'application :

Se connecte à la Live Client API locale pendant qu'une partie est en cours
Extrait l'état de la partie toutes les 5-10 secondes (kills, gold, niveaux, objectifs...)
Applique un modèle de Machine Learning entraîné sur des milliers de matchs Master+
Affiche le pourcentage de victoire en direct et propose des conseils stratégiques

Pourquoi ce projet ?

Sujet original qui sort des classiques (élections, météo, JO)
Multi-sources de données (historique + temps réel)
Vrai problème ML supervisé (classification binaire win/loss)
Démo live impressionnante pour la soutenance
Storytelling naturel : à quel moment d'une partie le résultat devient-il statistiquement prévisible ?


🎯 Objectifs pédagogiques validés
Ce projet répond à l'ensemble des critères de la grille d'évaluation UF B3 IA & Data :
CritèreImplémentationAcquérir des donnéesRiot API (matchs historiques) + Live Client API (temps réel)Préparer et nettoyerParsing des timelines, snapshots multi-timestamps, gestion des bots/erreursExplorer et analyserEDA sur les patterns de victoire, viz d'évolution des matchsVisualiserGraphiques d'analyse + interface Streamlit interactiveAppliquer un modèle MLLogistic Regression (baseline) + XGBoost (modèle final)PrédireProbabilité de victoire en direct à partir de l'état du matchConcevoir et déployer une interfaceApplication Streamlit en localDocumenterREADME + notebook + manuel d'installation

🏗️ Architecture
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

🔬 Méthodologie
Sources de données
Riot Games API (web) — pour l'entraînement

Endpoint match-v5/matches : métadonnées des matchs
Endpoint match-v5/timelines : état du match minute par minute
Endpoint league-v4/masterleagues : liste des joueurs Master+

Live Client Data API (locale) — pour l'inférence en direct

URL : https://127.0.0.1:2999/liveclientdata/allgamedata
Disponible pendant qu'une partie est active
Renvoie l'état complet de la partie à l'instant T

Features utilisées (9 features)
Différentiels équipe bleue (ORDER) - équipe rouge (CHAOS) :
FeatureDescriptionkills_diffDifférence de kills totaux entre les deux équipesdeaths_diffDifférence de morts totalescs_diffDifférence de creep score totallevel_diffDifférence de niveau moyentowers_diffDifférence de tours détruitesdragons_diffDifférence de dragons capturésheralds_diffDifférence de hérauts capturésbarons_diffDifférence de barons capturésgame_time_minutesTemps de jeu écoulé (contextuel)
Cible : blue_wins (0 ou 1)
Modèles testés

Baseline : Logistic Regression — modèle simple et interprétable
Modèle final : XGBoost — meilleure performance sur features tabulaires
Métriques : Accuracy, AUC-ROC, Log-loss, matrice de confusion
Validation : Cross-validation 5-folds


📦 Installation
Prérequis

Python 3.10+
League of Legends installé (pour utiliser l'app en mode live)
Une clé API Riot Games (developer.riotgames.com)

Setup
bash# Cloner le repo
git clone https://github.com/<ton-username>/lol-win-predictor.git
cd lol-win-predictor

# Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Installer les dépendances
pip install -r requirements.txt

# Configurer la clé API
cp .env.example .env
# Éditer .env et y mettre ta clé Riot RGAPI-...
Configuration
Créer un fichier .env à la racine :
envRIOT_API_KEY=RGAPI-ta-clé-ici
REGION=euw1
MATCH_REGION=europe
⚠️ La clé API Riot dev expire toutes les 24h, faut la régénérer chaque jour.

🚀 Utilisation
1. Pull des données d'entraînement
bashpython src/data/pull_matches.py --tier MASTER --count 3000
Récupère les matchs Master+ avec leur timeline. Tourne en background pendant plusieurs heures.
2. Entraînement du modèle
bashjupyter notebook notebooks/02_modeling.ipynb
Lance le notebook qui fait EDA, feature engineering, entraînement et évaluation.
3. Lancement de l'application
bashstreamlit run app/main.py
Ouvre l'app sur http://localhost:8501. Lance une partie de LoL et l'app détectera automatiquement l'état du match en cours.

📂 Structure du projet
lol-win-predictor/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
│
├── data/
│   ├── raw/              # JSON brut des matchs Riot API
│   └── processed/        # DataFrames features
│
├── notebooks/
│   ├── 01_eda.ipynb              # Analyse exploratoire
│   ├── 02_modeling.ipynb         # Entraînement & évaluation
│   └── 03_storytelling.ipynb     # Viz finales pour l'oral
│
├── src/
│   ├── data/
│   │   ├── pull_matches.py       # Pull Riot API
│   │   └── parse_timelines.py    # Parsing timelines → features
│   ├── features/
│   │   └── build_features.py     # Feature engineering
│   ├── models/
│   │   ├── train.py              # Entraînement
│   │   └── predict.py            # Inférence
│   └── live/
│       └── live_client.py        # Wrapper Live Client API
│
├── app/
│   ├── main.py                   # Application Streamlit
│   └── components/               # Composants UI
│
├── models/
│   └── xgboost_final.pkl         # Modèle sauvegardé
│
└── docs/
    └── installation.md           # Manuel d'installation détaillé

📅 Roadmap
PhaseStatutDescriptionJ1✅Validation Live Client API, structure du projetJ2⏳Pull des données Riot API (Master+ avec timelines)J3⏳Feature engineering + EDA + viz storytellingJ4⏳Modélisation : Logistic Regression + XGBoostJ5⏳Application Streamlit + polling Live Client APIJ6⏳Documentation, notebook propre, slides oralJ7⏳Buffer / polish / imprévus

🎓 Choix techniques justifiés
Pourquoi XGBoost ?

Excellente performance sur features tabulaires (notre cas)
Gère nativement les valeurs manquantes
Feature importances interprétables → utile pour générer des conseils
Rapide à entraîner

Pourquoi des différentiels (bleu - rouge) ?

Réduit la dimensionnalité (1 feature au lieu de 2)
Symétrise le problème (la partie est gagnée par l'écart, pas par les valeurs absolues)
Plus stable face aux outliers (un match avec beaucoup de kills total reste prédictible)

Pourquoi pas un overlay transparent ?
Décision pragmatique pour respecter la deadline (2 semaines avec alternance) :

Une fenêtre Streamlit à côté du jeu remplit la grille "interface fonctionnelle"
Pas de risque vis-à-vis des CGU Riot
Plus de temps consacré au cœur ML

Pourquoi se baser sur les events plutôt que sur les stats individuelles ?

Cohérence train/live garantie : les événements (kills, tours, dragons) sont disponibles des deux côtés sous la même forme
Stats détaillées des autres joueurs (armor, AP des adversaires...) non accessibles en live sans calcul item-par-item
10 features bien choisies > 50 features bruyantes


📊 Livrables

 Dépôt Git avec tout le code et la documentation
 Jupyter Notebook retraçant la démarche complète
 Application de data storytelling déployée localement
 Documentation technique + manuel d'installation


⚖️ Conformité
Ce projet utilise uniquement les APIs officielles publiques de Riot Games :

Pas de lecture mémoire du client League
Pas de modification du jeu
Pas d'automatisation in-game
Aucun avantage compétitif fourni

Il s'agit d'un outil d'analyse statistique utilisant les mêmes données que des outils tolérés par Riot (Mobalytics, U.GG, Blitz...).

👤 Auteur
Eliott Bellais
B3 Informatique — Spécialité Data & IA
Ynov Aix-en-Provence — 2025/2026

📝 Licence
Projet académique. Tous les noms, logos et données League of Legends appartiennent à Riot Games, Inc.
