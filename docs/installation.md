# Manuel d'installation

## Prérequis

- Python 3.10+
- League of Legends installé
- Clé API Riot Games (developer.riotgames.com — expire toutes les 24h)

## Setup

```bash
git clone https://github.com/Verdugue/Pr-diction-LOL
cd Pr-diction-LOL

python -m venv venv
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows

pip install -r requirements.txt

cp .env.example .env
# Editer .env : coller ta clé RGAPI-...
```

## Pipeline complet

### 1. Pull des données

```bash
python src/data/pull_matches.py --count 500
# ~2-3h pour 500 matchs (rate limit dev key)
# Les timelines sont sauvegardées dans data/raw/
```

### 2. Parsing → features

```bash
python src/data/parse_timelines.py
# Génère data/processed/features.parquet
```

### 3. Entraînement

```bash
python src/models/train.py
# Génère models/xgboost_final.pkl + models/evaluation.png
```

### 4. App live

```bash
streamlit run app/main.py
# Ouvre http://localhost:8501
# Lance une partie de LoL → l'app poll automatiquement
```

## Note sur la clé API

La dev key expire toutes les 24h. La régénérer sur developer.riotgames.com et mettre à jour `.env`.
