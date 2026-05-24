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

- Source 1 : Riot API `match-v5` — matchs Master+ EUW
- Source 2 : Live Client API locale `127.0.0.1:2999`
- Volume : **N matchs** × 5 snapshots = **N×5 lignes** *(à compléter après pull)*
- Qualité : uniquement ranked solo > 15 min (pas de surrenders/remakes)

**Screenshot à insérer :** `screenshots/data_pull_terminal.png` *(tqdm progress bar)*  
**Screenshot à insérer :** `screenshots/dataframe_head.png` *(df.head() dans notebook)*

---

## Slide 3 — Feature engineering (3 min)

Pourquoi des **différentiels** plutôt que des valeurs absolues ?

> "Un match avec 20 kills total et un match avec 5 kills total à 15 min — ce qui compte c'est qui est devant, pas le niveau d'activité brut."

| Feature | Justification |
|---------|--------------|
| `gold_diff` | Proxy économique le plus robuste |
| `kills_diff` | Avantage combat direct |
| `cs_diff` | Farm = économie passive |
| `towers_diff` | Contrôle de carte |
| `dragons_diff` | Objectifs long-terme |
| `kills_last_3min` | Momentum récent |
| `game_time_minutes` | Contexte temporel |

**Screenshot à insérer :** `screenshots/feature_distributions.png` *(histogrammes EDA)*

---

## Slide 4 — Modélisation (4 min)

Deux modèles, approche comparative :

**Logistic Regression (baseline)**
- Simple, interprétable, rapide
- Coefficients = importance directe des features
- AUC : *à compléter*

**XGBoost (modèle final)**
- Gradient boosting, idéal sur données tabulaires
- Gère les interactions entre features automatiquement
- Calibré avec `CalibratedClassifierCV(isotonic)` pour des probabilités fiables
- AUC : *à compléter*

**Screenshot à insérer :** `screenshots/roc_curves.png`  
**Screenshot à insérer :** `screenshots/calibration_curve.png`  
**Screenshot à insérer :** `screenshots/feature_importance.png`

---

## Slide 5 — La question centrale (3 min)

> "À quelle minute la partie est-elle statistiquement pliée ?"

Graphique : AUC-ROC par tranche de temps (10 / 15 / 20 / 25 / 30 min)

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
- Données Master+ → biais sur les parties normales/gold
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
