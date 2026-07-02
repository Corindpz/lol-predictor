# Plan de l'oral — LoL Win Predictor

**Contexte :** Projet fil rouge B3 IA & Data — Ynov Aix-en-Provence  
**Équipe :** Corin Deprez + Eliott Bellais  
**Durée visée :** ~20 min présentation + questions

---

## Structure narrative

L'oral suit un fil conducteur : **"À quel moment d'une partie de LoL le résultat est-il statistiquement inévitable ?"**

Ce n'est pas juste un projet ML — c'est une question de storytelling sportif.

---

## Slide 1 — Le problème (1 min)

> "League of Legends, c'est 10 joueurs, ~35 minutes, des milliers d'événements. Est-ce qu'un modèle peut voir ce que les joueurs ne voient pas encore ?"

- Contexte : 150M+ joueurs dans le monde, datasport émergent
- Problème ML : classification binaire (blue_wins : 0/1) sur données temporelles
- Angle original : prédiction **en cours de partie**, pas en post-game

**Screenshot à insérer :** `screenshots/lol_gameplay.png` *(capture d'une partie en cours)*

---

## Slide 2 — Les données (2 min)

- Source 1 : Riot API `match-v5` — ranked solo EUW, **Silver → Challenger**
- Source 2 : Live Client API locale `127.0.0.1:2999`
- Volume : **9 773 matchs** → **246 350 snapshots** (1 par minute, de la min 5 à 40)
- Qualité : uniquement ranked solo > 15 min (pas de surrenders/remakes)

**Screenshot à insérer :** `screenshots/data_pull_terminal.png` *(tqdm progress bar)*  
**Screenshot à insérer :** `screenshots/dataframe_head.png` *(df.head() dans notebook)*

---

## Slide 3 — Feature engineering (3 min)

Pourquoi des **différentiels** plutôt que des valeurs absolues ?

> "Un match avec 20 kills total et un match avec 5 kills total à 15 min — ce qui compte c'est qui est devant, pas le niveau d'activité brut."

| Feature | Justification |
|---------|--------------|
| `gold_diff` | Proxy économique le plus robuste (AUC 0,821 à lui seul) |
| `gold_slope` | Momentum économique — pente d'or sur 5 min (capte les comebacks) |
| `players_alive_diff` | Joueurs vivants — un 4v5 en late décide la partie |
| `kills_diff` | Avantage combat direct |
| `towers_diff` | Contrôle de carte |
| `dragons_diff` / `dragon_soul` | Objectifs long-terme |
| `baron_active` | Buff baron actif (≠ baron cumulé) |
| `game_time_minutes` | Contexte temporel |

*22 features au total, toutes des différentiels bleu − rouge.*

**Screenshot à insérer :** `screenshots/feature_distributions.png` *(histogrammes EDA)*

---

## Slide 4 — Modélisation (4 min)

Deux modèles, approche comparative :

**Logistic Regression (baseline)**
- Simple, interprétable, rapide
- Coefficients = importance directe des features
- AUC : **0,834**

**XGBoost (modèle final)**
- Gradient boosting, idéal sur données tabulaires
- Gère les interactions entre features automatiquement
- Calibré avec `CalibratedClassifierCV(isotonic)` pour des probabilités fiables (ECE 0,03)
- AUC : **0,835** (jusqu'à **0,91** en milieu de partie) · accuracy 74,9 % · Brier 0,166
- Split **temporel par partie** (pas de fuite entre snapshots d'une même game)

**Screenshot à insérer :** `screenshots/roc_curves.png`  
**Screenshot à insérer :** `screenshots/calibration_curve.png`  
**Screenshot à insérer :** `screenshots/feature_importance.png`

---

## Slide 5 — La question centrale (3 min)

> "À quelle minute la partie est-elle statistiquement pliée ?"

Graphique : AUC-ROC par minute de jeu — **0,76 à 10 min → 0,91 à 25 min**

→ Montre que le modèle devient plus confiant avec le temps de jeu  
→ Identifie les **points de bascule** (Baron, Dragon Soul, inhibiteur)

**Screenshot à insérer :** `screenshots/auc_by_time.png` *(graphique storytelling)*

---

## Slide 6 — Application live (4 min + démo)

**Démo en direct si possible, sinon vidéo screen-record.**

- Polling Live Client API toutes les 7 secondes
- Gauge de probabilité temps réel
- Graphique de tendance (évolution sur toute la partie)
- Conseils stratégiques basés sur les écarts de features

**Screenshot à insérer :** `screenshots/streamlit_app.png` *(app en cours de partie)*  
**Screenshot à insérer :** `screenshots/streamlit_trend.png` *(courbe de tendance)*

---

## Slide 7 — Limites & perspectives (2 min)

**Limites honnêtes :**
- Données EUW uniquement (Silver→Challenger) → biais régional, pas de KR/NA
- Gold live estimé (Live Client API ne donne pas le total exact)
- Pas de features individuelles (rôle, champion, build) — cohérence train/live
- Modèle statique : pas de retrain automatique sur les patchs

**Perspectives :**
- LSTM sur la séquence complète des frames (approche time-series)
- Features par rôle (ADC gold vs support gold)
- Retraining automatique à chaque patch Riot

---

## Ressources / références

- Riot Games Developer Portal : developer.riotgames.com
- Papers : "Predicting LoL match outcomes" (Google Scholar)
- Kaggle LoL datasets : kaggle.com/search?q=league+of+legends
- XGBoost docs : xgboost.readthedocs.io
- Scikit-learn calibration : scikit-learn.org/stable/modules/calibration.html
