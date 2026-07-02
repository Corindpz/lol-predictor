"""
Streamlit — Pipeline ML LoL Win Predictor
Explique pas à pas comment on a construit le modèle.
"""

import streamlit as st
import pandas as pd
import numpy as np
import joblib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import json
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="LoL Win Predictor — Pipeline ML",
    page_icon="⚔️",
    layout="wide",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: #070b14; color: #e8e0d0; }
[data-testid="stSidebar"] { background: #0d1117; }
[data-testid="stSidebarContent"] h1, h2, h3, h4 { color: #c89b3c; }
.metric-card { background: #0d1117; border: 1px solid #1e2a3a; border-radius: 12px; padding: 16px; }
.step-header { color: #c89b3c; font-size: 0.7rem; letter-spacing: 0.25em; text-transform: uppercase; }
code { background: #0d1117 !important; color: #0bc4e3 !important; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar nav ───────────────────────────────────────────────────────────────
st.sidebar.title("⚔️ Pipeline ML")
st.sidebar.markdown("---")
section = st.sidebar.radio("Navigation", [
    "0 · Contexte",
    "1 · Collecte des données",
    "2 · Parsing & features",
    "3 · Exploration EDA",
    "4 · Modélisation",
    "5 · Résultats & SHAP",
    "6 · Prédiction live",
    "7 · Perspectives",
    "8 · Draft & Synergies",
])
st.sidebar.markdown("---")
st.sidebar.caption("Projet fil rouge B3 IA & Data — Ynov 2026")
st.sidebar.caption("Corin × Eliott Bellais")

# ── Chargement données ─────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    df = pd.read_parquet("data/processed/features.parquet")
    return df

@st.cache_resource
def load_model():
    m = joblib.load("models/xgboost_final.pkl")
    return m

@st.cache_data
def load_params():
    p = json.loads(Path("models/best_params.json").read_text())
    return p

@st.cache_data
def load_synergy():
    p = Path("data/processed/synergy_scores.json")
    if not p.exists():
        return {}
    return json.loads(p.read_text())

@st.cache_data
def load_roles():
    p = Path("data/processed/champion_roles.json")
    if not p.exists():
        return {}
    return json.loads(p.read_text())

try:
    df = load_data()
    model = load_model()
    params = load_params()
    DATA_OK = True
except Exception as e:
    DATA_OK = False
    st.error(f"Données non trouvées : {e}")

# ════════════════════════════════════════════════════════════════════════════════
# 0 · Contexte
# ════════════════════════════════════════════════════════════════════════════════
if section == "0 · Contexte":
    st.markdown('<p class="step-header">Projet fil rouge B3 IA & Data · Ynov Aix-en-Provence 2026</p>', unsafe_allow_html=True)
    st.title("Prédire l'issue d'une game LoL")

    st.markdown("""
**Problème** : À partir de l'état d'une partie de League of Legends à un instant *T* (minute 10, 15, 20...),
peut-on prédire quelle équipe va gagner ?

**Pourquoi c'est dur** : Les parties durent 20 à 50 minutes. Une erreur peut retourner une game.
Le modèle doit capter des dynamiques temporelles complexes.

**Notre approche** : Prédiction binaire (équipe bleue gagne/perd) à partir de features agrégées par minute.
""")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Matchs collectés", "9 773")
    col2.metric("Snapshots", "246 350")
    col3.metric("Features", "22")
    col4.metric("AUC-ROC", "0.835")

    st.markdown("---")
    st.subheader("Architecture du pipeline")
    st.code("""
pull_matches.py     ← Riot API match-v5 (ranked EUW, Silver→Challenger)
        ↓
parse_timelines.py  ← 22 features par snapshot (1 / minute, de la min 5 à 40)
        ↓
features.parquet    ← 246 350 lignes (+ match_id, game_creation pour le split)
        ↓
train.py            ← LogReg (baseline) + XGBoost, split TEMPOREL groupé par match
        ↓
xgboost_final.pkl   ← CalibratedClassifierCV (isotonic) + TreeExplainer SHAP
        ↓
FastAPI + Next.js   ← App web prédiction live + simulateur SHAP
""", language="text")

# ════════════════════════════════════════════════════════════════════════════════
# 1 · Collecte
# ════════════════════════════════════════════════════════════════════════════════
elif section == "1 · Collecte des données":
    st.markdown('<p class="step-header">Step 1 / 7</p>', unsafe_allow_html=True)
    st.title("Collecte des données — Riot API")

    st.markdown("""
### Riot API match-v5

On utilise deux endpoints principaux :
- `/lol/match/v5/matches/{matchId}` → infos générales (participants, résultat)
- `/lol/match/v5/matches/{matchId}/timeline` → frames minute par minute (events, stats joueurs)

Les données sont collectées sur **EUW** (Europe West) : Silver → Challenger.
""")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("pull_matches.py")
        st.code("""
# Récupérer les PUUID des joueurs Master+
GET /lol/league/v4/challengerleagues/by-queue/RANKED_SOLO_5x5
GET /lol/summoner/v4/summoners/{summonerId}

# Récupérer les matchs récents
GET /lol/match/v5/matches/by-puuid/{puuid}/ids
    ?queue=420   # Ranked Solo/Duo uniquement
    &count=10

# Stocker timeline + info → data/raw/
{matchId}_timeline.json  ← frames minute par minute
{matchId}_info.json      ← participants, durée, résultat
""", language="python")

    with col2:
        st.subheader("Pourquoi les timelines ?")
        st.markdown("""
La timeline Riot API est unique : elle contient un **snapshot** de l'état du jeu
toutes les **60 secondes** + tous les **événements** (kills, tours, objectifs).

```json
frame {
  "participantFrames": {
    "1": {"totalGold": 4200, "level": 8, "xp": 3100, ...},
    ...
  },
  "events": [
    {"type": "CHAMPION_KILL", "killerId": 3, ...},
    {"type": "BUILDING_KILL", "buildingType": "TOWER_BUILDING", ...}
  ]
}
```

Cela nous permet de reconstituer l'état exact du jeu à la minute T.
""")

    st.markdown("---")
    st.subheader("Distribution du dataset")
    if DATA_OK:
        col1, col2 = st.columns(2)
        with col1:
            # Distribution par minute
            fig, ax = plt.subplots(figsize=(5, 3), facecolor="#0d1117")
            ax.set_facecolor("#0d1117")
            counts = df["game_time_minutes"].value_counts().sort_index()
            ax.bar(counts.index, counts.values, color="#c89b3c", alpha=0.8)
            ax.set_xlabel("Minute de snapshot", color="#e8e0d0")
            ax.set_ylabel("Nombre de snapshots", color="#e8e0d0")
            ax.tick_params(colors="#e8e0d0")
            ax.set_title("Snapshots par minute", color="#c89b3c")
            for spine in ax.spines.values():
                spine.set_edgecolor("#1e2a3a")
            st.pyplot(fig)

        with col2:
            # Winrate bleu
            fig, ax = plt.subplots(figsize=(5, 3), facecolor="#0d1117")
            ax.set_facecolor("#0d1117")
            wr = df.groupby("game_time_minutes")["blue_wins"].mean() * 100
            ax.plot(wr.index, wr.values, color="#0bc4e3", linewidth=2)
            ax.axhline(50, color=(1, 1, 1, 0.2), linestyle="--")
            ax.set_xlabel("Minute", color="#e8e0d0")
            ax.set_ylabel("Win rate équipe bleue (%)", color="#e8e0d0")
            ax.tick_params(colors="#e8e0d0")
            ax.set_title("Win rate par minute", color="#c89b3c")
            for spine in ax.spines.values():
                spine.set_edgecolor("#1e2a3a")
            st.pyplot(fig)

# ════════════════════════════════════════════════════════════════════════════════
# 2 · Parsing & features
# ════════════════════════════════════════════════════════════════════════════════
elif section == "2 · Parsing & features":
    st.markdown('<p class="step-header">Step 2 / 7</p>', unsafe_allow_html=True)
    st.title("Parsing des timelines → 26 features")

    st.markdown("""
### Principes de conception

Toutes les features sont des **différentiels bleu - rouge** :
- `gold_diff > 0` → équipe bleue en avance
- `gold_diff < 0` → équipe rouge en avance
- `first_blood = +1` → first blood bleu, `-1` = rouge, `0` = pas encore

Cela permet au modèle d'apprendre les asymétries dans une seule dimension.
""")

    features = {
        "Économie": [
            ("gold_diff", "Écart d'or total", "participantFrames.totalGold"),
            ("gold_slope", "Momentum d'or (pente sur 5 min)", "Dérivée du gold_diff"),
            ("current_gold_diff", "Or non dépensé", "participantFrames.currentGold"),
            ("level_diff", "Écart de niveaux", "participantFrames.level"),
            ("cs_diff", "Écart de farm (CS)", "minions + monstres neutres"),
        ],
        "Combat": [
            ("kills_diff", "Écart de kills", "CHAMPION_KILL"),
            ("kills_last_3min", "Momentum de kills (diff 3 min)", "Fenêtre glissante bleu − rouge"),
            ("damage_diff", "Dégâts aux champions", "damageStats.totalDamageDoneToChampions"),
            ("players_alive_diff", "Joueurs vivants", "Death timers (respawn estimé par niveau)"),
            ("first_blood", "First Blood (+1/-1/0)", "Premier CHAMPION_KILL"),
        ],
        "Structures": [
            ("towers_diff", "Tours détruites", "BUILDING_KILL (TOWER)"),
            ("plates_diff", "Turret Plates", "TURRET_PLATE_DESTROYED"),
            ("inhibitors_diff", "Inhibiteurs", "BUILDING_KILL (INHIB)"),
            ("first_tower", "Première tour (+1/-1/0)", "Premier BUILDING_KILL"),
        ],
        "Objectifs épiques": [
            ("dragons_diff", "Dragons", "ELITE_MONSTER_KILL (DRAGON)"),
            ("dragon_soul", "Dragon Soul (+1/-1/0)", "Dérivé du 4e dragon"),
            ("heralds_diff", "Rift Heralds", "ELITE_MONSTER_KILL (RIFTHERALD)"),
            ("barons_diff", "Barons Nashor", "ELITE_MONSTER_KILL (BARON)"),
            ("baron_active", "Buff Baron actif (+1/-1/0)", "Baron pris < 3 min"),
            ("elder_active", "Buff Elder actif (+1/-1/0)", "Elder pris < 2,5 min"),
            ("void_grubs_diff", "Void Grubs", "ELITE_MONSTER_KILL (HORDE)"),
        ],
        "Temps": [
            ("game_time_minutes", "Minute de jeu", "Index de frame"),
        ],
    }

    for version, feats in features.items():
        with st.expander(f"**{version}** — {len(feats)} features", expanded=(version == "Objectifs épiques")):
            feat_df = pd.DataFrame(feats, columns=["Feature", "Description", "Source API"])
            st.dataframe(feat_df, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("Snapshot à la minute 15 — exemple")
    st.code("""\
# Snapshot minute 15 — equipe bleue en avance → blue_wins = 1
{
  "gold_diff": 1800,
  "gold_slope": 220,
  "current_gold_diff": 300,
  "level_diff": 2,
  "cs_diff": 45,
  "kills_diff": 3,
  "kills_last_3min": 1,
  "damage_diff": 12000,
  "players_alive_diff": 1,
  "first_blood": 1,
  "towers_diff": 1,
  "plates_diff": 2,
  "inhibitors_diff": 0,
  "first_tower": 1,
  "dragons_diff": 1,
  "dragon_soul": 0,
  "heralds_diff": 1,
  "barons_diff": 0,
  "baron_active": 0,
  "elder_active": 0,
  "void_grubs_diff": 2,
  "game_time_minutes": 15
}
""", language="python")
    st.info("Note : toutes les features sont des différentiels bleu − rouge (positif = avantage bleu). `gold_slope` = pente du gold_diff sur 5 min (momentum), `players_alive_diff` = joueurs vivants estimés via les death timers.")

# ════════════════════════════════════════════════════════════════════════════════
# 3 · EDA
# ════════════════════════════════════════════════════════════════════════════════
elif section == "3 · Exploration EDA":
    st.markdown('<p class="step-header">Step 3 / 7</p>', unsafe_allow_html=True)
    st.title("Exploration des données (EDA)")

    if not DATA_OK:
        st.warning("Dataset non chargé.")
    else:
        st.markdown(f"**{len(df):,} snapshots** · **{df['match_id'].nunique():,} matchs** · 28 colonnes")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Corrélation features × victoire")
            key_features = ["gold_diff", "kills_diff", "xp_diff", "damage_diff",
                           "dragons_diff", "barons_diff", "first_blood",
                           "void_grubs_diff", "infernal_diff", "elder_active",
                           "first_tower", "towers_diff"]
            available_feats = [f for f in key_features if f in df.columns]
            correlations = df[available_feats + ["blue_wins"]].corr()["blue_wins"].drop("blue_wins").sort_values()

            fig, ax = plt.subplots(figsize=(5, 5), facecolor="#0d1117")
            ax.set_facecolor("#0d1117")
            colors = ["#e84057" if v < 0 else "#0bc4e3" for v in correlations.values]
            ax.barh(correlations.index, correlations.values, color=colors, alpha=0.85)
            ax.axvline(0, color=(1, 1, 1, 0.2))
            ax.set_xlabel("Corrélation de Pearson", color="#e8e0d0")
            ax.tick_params(colors="#e8e0d0")
            ax.set_title("Corrélation avec blue_wins", color="#c89b3c")
            for spine in ax.spines.values():
                spine.set_edgecolor("#1e2a3a")
            st.pyplot(fig)
            st.caption("towers_diff positif = blue a détruit plus de tours (sémantique corrigée en v4.1 — fix BUILDING_KILL teamId)")

        with col2:
            st.subheader("Distribution gold_diff par résultat")
            blue_wins = df[df["blue_wins"] == 1]["gold_diff"]
            red_wins  = df[df["blue_wins"] == 0]["gold_diff"]

            fig, ax = plt.subplots(figsize=(5, 5), facecolor="#0d1117")
            ax.set_facecolor("#0d1117")
            ax.hist(blue_wins, bins=50, alpha=0.6, color="#0bc4e3", label="Blue gagne", density=True)
            ax.hist(red_wins,  bins=50, alpha=0.6, color="#e84057", label="Red gagne",  density=True)
            ax.set_xlabel("gold_diff (bleu - rouge)", color="#e8e0d0")
            ax.set_ylabel("Densité", color="#e8e0d0")
            ax.tick_params(colors="#e8e0d0")
            ax.legend(facecolor="#0d1117", labelcolor="#e8e0d0")
            ax.set_title("Gold diff selon le gagnant", color="#c89b3c")
            for spine in ax.spines.values():
                spine.set_edgecolor("#1e2a3a")
            st.pyplot(fig)

        st.subheader("Stats descriptives — features v4 & v5")
        v4_features = ["void_grubs_diff", "first_tower", "infernal_diff", "ocean_diff",
                       "elder_active", "powerspike_diff", "mountain_diff", "cloud_diff",
                       "chemtech_diff", "hextech_diff"]
        available = [f for f in v4_features if f in df.columns]
        if available:
            desc = df[available].describe().round(3)
            non_zero = pd.Series({f: (df[f] != 0).mean() * 100 for f in available}, name="% non-zéro").round(1)
            desc.loc["% non-zéro"] = non_zero
            st.dataframe(desc, use_container_width=True)

# ════════════════════════════════════════════════════════════════════════════════
# 4 · Modélisation
# ════════════════════════════════════════════════════════════════════════════════
elif section == "4 · Modélisation":
    st.markdown('<p class="step-header">Step 4 / 7</p>', unsafe_allow_html=True)
    st.title("Modélisation")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Choix des modèles")
        st.markdown("""
**Régression Logistique (baseline)**
- Interprétable, rapide, bon calibrage natif
- Limite : hypothèse de linéarité

**XGBoost (calibré)**
- Gradient boosting : combine des arbres faibles
- Gère les interactions non-linéaires entre features
- `CalibratedClassifierCV(method='isotonic')` pour obtenir des probabilités calibrées

**Pourquoi calibrer ?**
Sans calibration, les probabilités du modèle ne correspondent pas aux fréquences réelles.
Un modèle "sur-confiant" dit 90% quand c'est en réalité 75%.
""")

    with col2:
        st.subheader("Pipeline d'entraînement")
        st.code("""
from sklearn.model_selection import StratifiedGroupKFold, RandomizedSearchCV
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
from xgboost import XGBClassifier

# Split TEMPOREL par partie : les parties récentes en test, aucune game
# à cheval sur train/test -> pas de fuite entre snapshots d'un même match.
train_df, test_df = temporal_group_split(df)

# 1. RandomizedSearchCV avec CV GROUPÉE par match_id (anti-fuite)
cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
search = RandomizedSearchCV(XGBClassifier(), param_dist, n_iter=40,
                            scoring="roc_auc", cv=cv, n_jobs=-1)
search.fit(X_train, y_train, groups=train_df["match_id"])
best_xgb = search.best_estimator_

# 2. Calibration isotonic sur un hold-out groupé (le sigmoid dégradait l'ECE)
model = CalibratedClassifierCV(FrozenEstimator(best_xgb), method="isotonic")
model.fit(X_calib, y_calib)
""", language="python")

    st.markdown("---")
    st.subheader("Hyperparamètres optimisés")
    if DATA_OK:
        params_display = {
            "n_estimators": params.get("n_estimators"),
            "max_depth": params.get("max_depth"),
            "learning_rate": round(params.get("learning_rate", 0), 4),
            "reg_alpha": round(params.get("reg_alpha", 0), 3),
            "reg_lambda": round(params.get("reg_lambda", 0), 3),
            "subsample": round(params.get("subsample", 0), 3),
            "colsample_bytree": round(params.get("colsample_bytree", 0), 3),
        }
        for k, v in params_display.items():
            col_k, col_v = st.columns([2, 3])
            col_k.text(k)
            col_v.text(v)

# ════════════════════════════════════════════════════════════════════════════════
# 5 · Résultats & SHAP
# ════════════════════════════════════════════════════════════════════════════════
elif section == "5 · Résultats & SHAP":
    st.markdown('<p class="step-header">Step 5 / 7</p>', unsafe_allow_html=True)
    st.title("Résultats & Explainability SHAP")

    col1, col2, col3 = st.columns(3)
    col1.metric("Accuracy XGBoost", "74.9%", "≈ LogReg")
    col2.metric("AUC-ROC", "0.835", "jusqu'à 0.91 en mid-game")
    col3.metric("Brier / ECE", "0.166 / 0.027", "bien calibré")

    st.markdown("""
### Interprétation

- **AUC-ROC 0.835** (split temporel groupé, sans fuite) : le modèle distingue bien les gagnants des perdants — et grimpe jusqu'à **0.91 à la minute 25**. Un chiffre honnête (une version fuitée annonçait 0.856).
- **Accuracy 74.9%** en agrégé : forcément plus faible en early game (peu d'info) que vers la min 25. Précision qui monte avec le temps de jeu.
- **Bien calibré** (Brier 0.166, ECE 0.027) : quand le modèle dit 80 %, c'est vrai ~8 fois sur 10.
- **LogReg vs XGBoost** : très proches — `gold_diff` seul fait déjà AUC 0.821. XGBoost apporte la valeur sur les interactions et le momentum (pente d'or, joueurs vivants).
""")

    st.markdown("---")
    st.subheader("SHAP — Feature Importance")
    st.markdown("""
SHAP (SHapley Additive exPlanations) décompose chaque prédiction en contributions par feature.

**Exemple** : pour une avance bleue nette à la minute 25 (blue win prob ≈ 91 %), SHAP montre :
- `gold_diff` : le plus fort contributeur (avance d'or)
- `dragons_diff` : bonus objectifs
- `level_diff` / `gold_slope` : avance d'XP et momentum positif
""")

    if DATA_OK:
        try:
            from src.models.explain import explain_prediction

            # Exemple : avance bleue nette à la minute 25
            sample = {
                "gold_diff": 5000, "gold_slope": 700, "current_gold_diff": 400,
                "level_diff": 5, "cs_diff": 60, "kills_diff": 7,
                "kills_last_3min": 2, "damage_diff": 18000, "players_alive_diff": 2,
                "first_blood": 1, "towers_diff": 4, "plates_diff": 2,
                "inhibitors_diff": 0, "first_tower": 1, "dragons_diff": 2,
                "dragon_soul": 0, "heralds_diff": 1, "barons_diff": 1,
                "baron_active": 1, "elder_active": 0, "void_grubs_diff": 2,
                "game_time_minutes": 25,
            }
            contribs = explain_prediction(sample, top_k=10)

            fig, ax = plt.subplots(figsize=(7, 4), facecolor="#0d1117")
            ax.set_facecolor("#0d1117")
            names = [c["label"] for c in contribs][::-1]
            vals  = [c["contribution"] for c in contribs][::-1]
            colors_bar = ["#0bc4e3" if v > 0 else "#e84057" for v in vals]
            ax.barh(names, vals, color=colors_bar, alpha=0.85)
            ax.axvline(0, color=(1, 1, 1, 0.2))
            ax.set_xlabel("Contribution SHAP (log-odds, + = équipe bleue)", color="#e8e0d0")
            ax.tick_params(colors="#e8e0d0")
            ax.set_title("Impact SHAP — exemple game à 25 min (avance bleue)", color="#c89b3c")
            for spine in ax.spines.values():
                spine.set_edgecolor("#1e2a3a")
            st.pyplot(fig)

        except Exception as e:
            st.info(f"SHAP non disponible : {e}")

    st.markdown("---")
    st.subheader("Évolution de la courbe win% sur une vraie game")
    st.markdown("""
La courbe ci-dessous montre l'évolution de la probabilité de victoire minute par minute.
Le modèle est appliqué à chaque snapshot de la timeline Riot API.
""")
    st.image("models/evaluation.png", caption="Graphiques d'évaluation — générés le 2026-05-25")

# ════════════════════════════════════════════════════════════════════════════════
# 6 · Prédiction live
# ════════════════════════════════════════════════════════════════════════════════
elif section == "6 · Prédiction live":
    st.markdown('<p class="step-header">Step 6 / 7</p>', unsafe_allow_html=True)
    st.title("Prédiction live — API FastAPI")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Architecture")
        st.code("""
# FastAPI — POST /predict
@app.post("/predict")
def predict(features: FeatureInput):
    f = features.model_dump()

    # Prédiction
    proba = predict_win_probability(f)

    # SHAP — contribution par feature
    X = pd.DataFrame([f])[FEATURE_COLS]
    shap_vals = explainer.shap_values(X)
    feature_impacts = {
        feat: round(delta_prob(sv_val) * 100, 2)
        for feat, sv_val in zip(FEATURE_COLS, shap_vals[0])
    }

    return {
        "blue_win_probability": round(proba * 100, 1),
        "advice": get_advice(f, proba),
        "feature_impacts": feature_impacts,
    }
""", language="python")

    with col2:
        st.subheader("Simulateur interactif")
        st.markdown("""
Le simulateur permet de tester le modèle en temps réel :

1. Ajuster les sliders (gold diff, kills, tours, dragons...)
2. Le frontend envoie un POST à FastAPI
3. Le modèle retourne la probabilité + SHAP
4. Le graphe SHAP montre quelles features ont le plus d'impact

**Chaque modification de slider** → nouvelle prédiction en ~50ms
""")
        st.markdown("**Exemple de réponse API :**")
        st.json({
            "blue_win_probability": 73.2,
            "advice": ["Avantage gold — forcez des objectifs"],
            "feature_impacts": {
                "gold_diff": 15.2,
                "infernal_diff": 8.8,
                "barons_diff": 6.1,
                "void_grubs_diff": 2.1,
                "cc_diff": -1.8
            }
        })

    if DATA_OK:
        st.markdown("---")
        st.subheader("Test live — prédiction immédiate")
        col1, col2, col3 = st.columns(3)
        gold_diff = col1.slider("gold_diff", -10000, 10000, 0, 500)
        kills_diff = col2.slider("kills_diff", -15, 15, 0)
        towers_diff = col3.slider("towers_diff", -6, 6, 0)
        col4, col5, col6 = st.columns(3)
        dragons_diff = col4.slider("dragons_diff", -4, 4, 0)
        barons_diff = col5.slider("barons_diff", -3, 3, 0)
        elder_active = col6.select_slider("elder_active", [-1, 0, 1], 0)

        features_input = {
            "kills_diff": kills_diff, "deaths_diff": 0, "cs_diff": 0,
            "gold_diff": gold_diff, "level_diff": 0, "towers_diff": towers_diff,
            "dragons_diff": dragons_diff, "heralds_diff": 0, "barons_diff": barons_diff,
            "kills_last_3min": 0, "game_time_minutes": 20, "wards_diff": 0,
            "inhibitors_diff": 0, "damage_diff": 0, "first_blood": 0,
            "xp_diff": 0, "plates_diff": 0, "current_gold_diff": 0,
            "dragon_soul": 0, "cc_diff": 0, "void_grubs_diff": 0,
            "first_tower": 0, "infernal_diff": 0, "ocean_diff": 0,
            "elder_active": elder_active, "powerspike_diff": 0,
            "mountain_diff": 0, "cloud_diff": 0, "chemtech_diff": 0, "hextech_diff": 0,
        }

        try:
            from src.models.predict import predict_win_probability
            from src.features.build_features import FEATURE_COLS
            proba = predict_win_probability(features_input)
            prob_pct = round(proba * 100, 1)
            color = "#0bc4e3" if prob_pct > 50 else "#e84057"
            st.markdown(f"""
<div style="background: #0d1117; border: 1px solid {color}; border-radius: 12px; padding: 24px; text-align: center;">
    <p style="color: #888; font-size: 0.75rem; letter-spacing: 0.2em;">VICTOIRE ÉQUIPE BLEUE</p>
    <p style="color: {color}; font-size: 3.5rem; font-weight: 900; margin: 8px 0;">{prob_pct}%</p>
</div>
""", unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Prédiction impossible : {e}")

# ════════════════════════════════════════════════════════════════════════════════
# 7 · Perspectives
# ════════════════════════════════════════════════════════════════════════════════
elif section == "7 · Perspectives":
    st.markdown('<p class="step-header">Step 7 / 7</p>', unsafe_allow_html=True)
    st.title("Perspectives & extensions")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("ML v5 ✅ — 30 features · AUC 0.857")
        st.markdown("""
**Implémenté en v5 (S15 2026) :**
- ✅ `mountain_diff` — Dragons Montagne (EARTH_DRAGON)
- ✅ `cloud_diff` — Dragons Nuage (AIR_DRAGON)
- ✅ `chemtech_diff` — Dragons Chemtech
- ✅ `hextech_diff` — Dragons Hextech
- ✅ Fix bug `towers_diff` / `first_tower` inversés (BUILDING_KILL teamId)

**ML v6 — pistes futures :**
""")
        ideas = [
            ("Champion identité", "Intégrer le champion name — modèle apprendrait les metas"),
            ("Time series ML", "LSTM ou Transformer sur la séquence complète de frames"),
            ("Void Grubs exact", "0-6 grubs individuels plutôt qu'un diff"),
            ("Items par champion", "Tracker les achats par champion — spike contextuel"),
        ]
        for name, desc in ideas:
            st.markdown(f"**{name}** : {desc}")

    with col2:
        st.subheader("Features produit à venir")
        features_prod = [
            ("Streak/Tilt Tracker", "Détecter les séries de défaites + dégradation KDA → alerter le joueur"),
            ("Draft Predictor", "Analyser la composition d'équipe avant la game → prédire les synergies"),
            ("Pro Tournament Analysis", "Comparer les patterns des pros via lolesports API"),
            ("Alert \"Point de bascule\"", "Notifier quand la game bascule définitivement (>80% win prob)"),
            ("Historique personnel", "Tracker les performances du joueur match après match"),
        ]
        for name, desc in features_prod:
            st.markdown(f"**{name}** : {desc}")

    st.markdown("---")
    st.subheader("Limites du modèle actuel")
    st.markdown("""
1. **Dataset EUW uniquement** : les dynamiques de jeu varient par région (KR > EUW en générale)
2. **Pas de features temporelles** : chaque snapshot est indépendant, on ne modélise pas l'évolution
3. **Wards sous-évalués** : le vision control compte moins dans notre dataset que dans les pros
4. **Meta-dépendant** : le modèle est entraîné sur S14/S15. Chaque saison change les valeurs relatives
5. **Features partielles pour tournois** : lolesports API ne donne pas wards, damage, XP
""")

    st.markdown("---")
    st.subheader("Ce qu'on retiendra")
    st.markdown("""
> **Le gold_diff reste le prédicteur le plus robuste à tous les timestamps.**
> Au-delà de 1500g d'avantage à 15 minutes, la probabilité de victoire dépasse 65%.
> Les nouvelles features v4/v5 (infernal, chemtech, hextech, void grubs, elder) ajoutent
> de la précision sur les situations d'égalité gold mais n'invalident pas ce principe fondamental.
""")

# ════════════════════════════════════════════════════════════════════════════════
# 8 · Draft & Synergies
# ════════════════════════════════════════════════════════════════════════════════
elif section == "8 · Draft & Synergies":
    st.markdown('<p class="step-header">Bonus — Draft Predictor</p>', unsafe_allow_html=True)
    st.title("Draft & Synergies : Statistiques vs ML")

    synergy_db = load_synergy()
    roles_db   = load_roles()

    st.markdown("---")

    # ── Stats globales ─────────────────────────────────────────────────────────
    st.subheader("1. Ce qu'on a calculé")

    pairs_df = pd.DataFrame([
        {"pair": k, "games": v["games"], "winrate": v["winrate"]}
        for k, v in synergy_db.items()
    ])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Paires de champions", f"{len(pairs_df):,}")
    col2.metric("Champions uniques", str(len(roles_db)))
    col3.metric("Matchs source", "10 105")
    col4.metric("Paires ≥ 20 games", str((pairs_df["games"] >= 20).sum()))

    # Distribution du nombre de games par paire
    st.subheader("Distribution des paires par nombre de parties observées")
    st.markdown("""
**Le problème de la sparsité** : la majorité des paires ont très peu de données.
Un win rate à 80% sur 5 games n'est pas fiable. C'est la limite principale de l'approche statistique.
""")

    fig, axes = plt.subplots(1, 2, figsize=(12, 4), facecolor="#070b14")
    for ax in axes:
        ax.set_facecolor("#0d1117")
        for s in ax.spines.values():
            s.set_color("#1e2a3a")

    # Histogramme games par paire
    counts = pairs_df["games"].clip(upper=150)
    axes[0].hist(counts, bins=40, color="#c89b3c", alpha=0.8, edgecolor="#070b14")
    axes[0].axvline(20, color="#e84057", linestyle="--", linewidth=1.5, label="Seuil fiabilité (20)")
    axes[0].set_title("Games par paire (cap 150)", color="#c89b3c", fontsize=11, fontweight="bold")
    axes[0].set_xlabel("Nombre de parties", color="#8a8070")
    axes[0].set_ylabel("Nb de paires", color="#8a8070")
    axes[0].tick_params(colors="#8a8070")
    axes[0].legend(fontsize=9, labelcolor="#e84057")

    # Distribution des win rates (paires ≥ 20 games)
    reliable = pairs_df[pairs_df["games"] >= 20]["winrate"]
    axes[1].hist(reliable, bins=30, color="#0bc4e3", alpha=0.8, edgecolor="#070b14")
    axes[1].axvline(0.5, color="#c89b3c", linestyle="--", linewidth=1.5, label="50% (neutre)")
    axes[1].set_title("Win rates (paires ≥ 20 games)", color="#0bc4e3", fontsize=11, fontweight="bold")
    axes[1].set_xlabel("Win rate observé", color="#8a8070")
    axes[1].set_ylabel("Nb de paires", color="#8a8070")
    axes[1].tick_params(colors="#8a8070")
    axes[1].legend(fontsize=9, labelcolor="#c89b3c")

    plt.tight_layout()
    st.pyplot(fig)
    plt.close()

    st.caption(f"""
**Lecture** : {(pairs_df['games'] < 20).sum()} paires ({(pairs_df['games'] < 20).mean()*100:.0f}%) ont moins de 20 parties.
Sur ces paires, les win rates sont très bruités. Les {(pairs_df['games'] >= 20).sum()} paires fiables
se concentrent naturellement autour de 50% — preuve que la plupart des compositions se valent.
""")

    # ── Top/flop synergies ─────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("2. Top synergies observées (≥ 20 games)")

    reliable_df = pairs_df[pairs_df["games"] >= 20].copy()
    reliable_df["champ1"] = reliable_df["pair"].str.split("|").str[0]
    reliable_df["champ2"] = reliable_df["pair"].str.split("|").str[1]
    reliable_df["winrate_pct"] = (reliable_df["winrate"] * 100).round(1)

    col_top, col_bot = st.columns(2)

    with col_top:
        top10 = reliable_df.nlargest(10, "winrate")[["champ1", "champ2", "winrate_pct", "games"]]
        top10.columns = ["Champion 1", "Champion 2", "WR%", "Games"]
        top10 = top10.reset_index(drop=True)
        top10.index += 1

        fig, ax = plt.subplots(figsize=(5.5, 3.5), facecolor="#070b14")
        ax.set_facecolor("#0d1117")
        labels = [f"{r['Champion 1']}\n+ {r['Champion 2']}" for _, r in top10.iterrows()]
        bars = ax.barh(labels[::-1], top10["WR%"].values[::-1], color="#0bc4e3", alpha=0.85)
        ax.axvline(50, color="#c89b3c", linestyle="--", linewidth=1, alpha=0.7)
        ax.set_xlim(45, 80)
        ax.set_title("🔝 Top 10 synergies", color="#0bc4e3", fontsize=10, fontweight="bold")
        ax.tick_params(colors="#8a8070", labelsize=7)
        for s in ax.spines.values():
            s.set_color("#1e2a3a")
        for bar, val in zip(bars, top10["WR%"].values[::-1]):
            ax.text(val + 0.3, bar.get_y() + bar.get_height()/2,
                    f"{val:.1f}%", va="center", color="white", fontsize=7, fontweight="bold")
        plt.tight_layout()
        st.pyplot(fig)
        plt.close()

    with col_bot:
        bot10 = reliable_df.nsmallest(10, "winrate")[["champ1", "champ2", "winrate_pct", "games"]]
        bot10.columns = ["Champion 1", "Champion 2", "WR%", "Games"]
        bot10 = bot10.reset_index(drop=True)

        fig, ax = plt.subplots(figsize=(5.5, 3.5), facecolor="#070b14")
        ax.set_facecolor("#0d1117")
        labels = [f"{r['Champion 1']}\n+ {r['Champion 2']}" for _, r in bot10.iterrows()]
        bars = ax.barh(labels[::-1], bot10["WR%"].values[::-1], color="#e84057", alpha=0.85)
        ax.axvline(50, color="#c89b3c", linestyle="--", linewidth=1, alpha=0.7)
        ax.set_xlim(25, 55)
        ax.set_title("💀 Pires anti-synergies", color="#e84057", fontsize=10, fontweight="bold")
        ax.tick_params(colors="#8a8070", labelsize=7)
        for s in ax.spines.values():
            s.set_color("#1e2a3a")
        for bar, val in zip(bars, bot10["WR%"].values[::-1]):
            ax.text(val - 0.3, bar.get_y() + bar.get_height()/2,
                    f"{val:.1f}%", va="center", ha="right", color="white", fontsize=7, fontweight="bold")
        plt.tight_layout()
        st.pyplot(fig)
        plt.close()

    # ── Rôles ─────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("3. Distribution des rôles par champion")

    ROLE_LABELS = {"TOP": "Top", "JUNGLE": "Jungle", "MIDDLE": "Mid",
                   "BOTTOM": "ADC", "UTILITY": "Support"}
    primary_counts = {}
    for champ, data in roles_db.items():
        primary = data.get("_primary", "?")
        primary_counts[primary] = primary_counts.get(primary, 0) + 1

    roles_sorted = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]
    counts_vals = [primary_counts.get(r, 0) for r in roles_sorted]
    colors_roles = ["#0bc4e3", "#c89b3c", "#8a6d2a", "#e84057", "#7b61ff"]

    fig, ax = plt.subplots(figsize=(7, 3.5), facecolor="#070b14")
    ax.set_facecolor("#0d1117")
    bars = ax.bar([ROLE_LABELS[r] for r in roles_sorted], counts_vals,
                  color=colors_roles, alpha=0.85, edgecolor="#070b14", width=0.6)
    ax.set_title("Champions par rôle primaire (dans le dataset)", color="#c89b3c",
                 fontsize=11, fontweight="bold")
    ax.tick_params(colors="#8a8070")
    for s in ax.spines.values():
        s.set_color("#1e2a3a")
    for bar, val in zip(bars, counts_vals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                str(val), ha="center", color="white", fontsize=10, fontweight="bold")
    plt.tight_layout()
    st.pyplot(fig)
    plt.close()

    # ── Explorateur interactif ─────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("4. Explorateur de synergies")

    champ_list = sorted(roles_db.keys())
    selected = st.selectbox("Choisissez un champion", champ_list, index=champ_list.index("Jinx") if "Jinx" in champ_list else 0)

    if selected:
        # Données du champion
        champ_data = roles_db.get(selected, {})
        primary = champ_data.get("_primary", "?")
        role_stats = [(r, v) for r, v in champ_data.items() if not r.startswith("_")]
        role_stats.sort(key=lambda x: -x[1]["games"])
        total_games = sum(v["games"] for _, v in role_stats)

        col_info, col_roles = st.columns([1, 2])
        with col_info:
            st.markdown(f"**Rôle primaire :** {ROLE_LABELS.get(primary, primary)}")
            st.markdown(f"**Total games :** {total_games:,}")
            for r, v in role_stats:
                pct = v["games"] / max(total_games, 1) * 100
                if pct >= 3:
                    st.markdown(f"- {ROLE_LABELS.get(r, r)} : {v['games']} games · {v['winrate']*100:.1f}% WR · {pct:.0f}% du pool")

        with col_roles:
            # Best synergies pour ce champion
            champ_pairs = []
            for k, v in synergy_db.items():
                a, b = k.split("|")
                if a == selected:
                    champ_pairs.append({"partner": b, **v})
                elif b == selected:
                    champ_pairs.append({"partner": a, **v})

            if champ_pairs:
                champ_pairs_df = pd.DataFrame(champ_pairs)
                champ_pairs_df = champ_pairs_df[champ_pairs_df["games"] >= 10].sort_values("winrate", ascending=False)
                champ_pairs_df["winrate_pct"] = (champ_pairs_df["winrate"] * 100).round(1)

                best5  = champ_pairs_df.head(5)
                worst5 = champ_pairs_df.tail(5).sort_values("winrate")

                fig, axes = plt.subplots(1, 2, figsize=(9, 3), facecolor="#070b14")
                for ax in axes:
                    ax.set_facecolor("#0d1117")
                    for s in ax.spines.values():
                        s.set_color("#1e2a3a")

                axes[0].barh(best5["partner"].values[::-1], best5["winrate_pct"].values[::-1],
                             color="#0bc4e3", alpha=0.85)
                axes[0].axvline(50, color="#c89b3c", linestyle="--", linewidth=1)
                axes[0].set_title(f"Meilleures synergies avec {selected}", color="#0bc4e3",
                                  fontsize=9, fontweight="bold")
                axes[0].tick_params(colors="#8a8070", labelsize=8)

                axes[1].barh(worst5["partner"].values[::-1], worst5["winrate_pct"].values[::-1],
                             color="#e84057", alpha=0.85)
                axes[1].axvline(50, color="#c89b3c", linestyle="--", linewidth=1)
                axes[1].set_title(f"Pires anti-synergies avec {selected}", color="#e84057",
                                  fontsize=9, fontweight="bold")
                axes[1].tick_params(colors="#8a8070", labelsize=8)

                plt.tight_layout()
                st.pyplot(fig)
                plt.close()

    # ── Modèle ML entraîné — résultats réels ──────────────────────────────────
    st.markdown("---")
    st.subheader("5. On a entraîné le modèle ML — voilà ce qu'on a trouvé")

    st.markdown("""
**Approche** : XGBoost entraîné sur un vecteur one-hot de 344 features (172 champions × 2 équipes).
Chaque match devient une ligne : `[blue_Jinx=1, blue_Thresh=1, ..., red_Caitlyn=1, ..., blue_wins=1]`.
Le modèle apprend quelles compositions gagnent plus souvent.
""")

    # Load draft stats if available
    draft_stats_path = Path("models/draft_stats.json")
    if draft_stats_path.exists():
        draft_stats = json.loads(draft_stats_path.read_text())
        auc_cv  = draft_stats["auc_cv"]
        acc_cv  = draft_stats["acc_cv"]
        n_samp  = draft_stats["n_samples"]
        n_feat  = draft_stats["n_features"]
        top_feats = draft_stats["top_features"]
    else:
        auc_cv, acc_cv, n_samp, n_feat = 0.513, 0.516, 10097, 344
        top_feats = []

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Dataset", f"{n_samp:,} matchs")
    col2.metric("Features", f"{n_feat}")
    auc_delta = f"{auc_cv - 0.857:.3f}" if auc_cv < 0.857 else f"+{auc_cv - 0.857:.3f}"
    col3.metric("AUC (5-fold CV)", f"{auc_cv:.3f}", delta=auc_delta, delta_color="inverse")
    col4.metric("Accuracy", f"{acc_cv*100:.1f}%")

    # ── Le résultat honnête ────────────────────────────────────────────────────
    st.error(f"""
**AUC = {auc_cv:.3f} — quasiment aléatoire.**

Un modèle qui prédit toujours "victoire rouge" (car 52.2% WR rouge) obtient {52.2:.1f}% d'accuracy.
Notre XGBoost obtient {acc_cv*100:.1f}%. La **composition seule ne prédit presque pas l'issue**.
C'est cohérent avec la littérature : le skill individuel explique ~70% du résultat d'une partie solo queue.
""")

    # Comparison AUC bar chart
    st.subheader("Comparaison des AUC par modèle")
    models_comp = {
        "XGBoost game-state\n(30 features in-game)": 0.857,
        "Baseline\n(toujours rouge gagne)": 0.5,
        "Draft XGBoost\n(344 one-hot champions)": auc_cv,
        "Draft LogReg\n(régularisation forte)": 0.513,
    }

    fig, ax = plt.subplots(figsize=(10, 3.5), facecolor="#070b14")
    ax.set_facecolor("#0d1117")
    for s in ax.spines.values():
        s.set_color("#1e2a3a")

    bar_colors = ["#0bc4e3", "#8a8070", "#e84057", "#e84057"]
    bars = ax.barh(list(models_comp.keys())[::-1], list(models_comp.values())[::-1],
                   color=bar_colors[::-1], alpha=0.85, height=0.5)
    ax.axvline(0.5, color="#8a8070", linestyle="--", linewidth=1, label="Aléatoire (0.5)")
    ax.axvline(0.857, color="#0bc4e3", linestyle=":", linewidth=1.5, alpha=0.6, label="Game-state model")
    ax.set_xlim(0.45, 0.92)
    ax.set_title("AUC-ROC par approche — plus c'est haut, mieux c'est", color="#c89b3c",
                 fontsize=11, fontweight="bold")
    ax.tick_params(colors="#8a8070", labelsize=9)
    ax.legend(fontsize=8, labelcolor="#8a8070")
    for bar, val in zip(bars, list(models_comp.values())[::-1]):
        ax.text(val + 0.003, bar.get_y() + bar.get_height()/2,
                f"{val:.3f}", va="center", color="white", fontsize=9, fontweight="bold")
    plt.tight_layout()
    st.pyplot(fig)
    plt.close()

    # ── Pourquoi ──────────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("6. Pourquoi le draft ML ne marche pas bien — 3 raisons")

    col_a, col_b, col_c = st.columns(3)

    with col_a:
        st.markdown("#### Skill > Draft")
        st.markdown("""
En solo queue, un joueur Diamond sur n'importe quel champion
bat un joueur Gold sur la "synergie parfaite".

Le modèle voit Jinx + Thresh gagner 48% → il apprend que
c'est une mauvaise composition. En réalité, c'est peut-être
le bot lane qui était mauvais ce jour-là.

**Le signal est noyé dans le bruit du skill.**
""")

    with col_b:
        st.markdown("#### Sparsité extrême")
        st.markdown("""
Il y a **C(172, 5) × C(167, 5) ≈ 10¹⁷** compositions 5v5 possibles.

On en a observé 10 097. Chaque composition est **unique ou presque**.
Le modèle one-hot ne peut pas apprendre de généralisation
sur des combinaisons qu'il n'a jamais vues.

→ Il overfit sur le train (AUC 0.63) puis échoue sur le test (0.51).
""")

    with col_c:
        st.markdown("#### Labels bruités")
        st.markdown("""
Le label `blue_wins` capture **tout** : draft, skill,
early game, late game, chance, surrenders anticipés...

Pour qu'un modèle draft apprenne quelque chose,
il faudrait isoler la contribution draft du résultat,
ce qui nécessiterait des données contrôlées
(même joueurs, compos différentes) — impossibles à collecter.
""")

    # ── Top champions discriminants ────────────────────────────────────────────
    if top_feats:
        st.markdown("---")
        st.subheader("7. Ce que le modèle a quand même appris")
        st.markdown("""
Malgré une AUC proche du hasard, certains champions ont une importance non nulle.
Ces champions ont une **force indépendante de la composition** — ils gagnent plus souvent
quelle que soit leur équipe. C'est en réalité du **champion tier list implicite**, pas de la synergie.
""")

        # Build individual WR from draft dataset
        try:
            draft_df = pd.read_parquet("data/processed/draft_features.parquet")
            champ_wr = []
            for col in [c for c in draft_df.columns if c.startswith("blue_") and c != "blue_wins"]:
                champ = col.split("_", 1)[1]
                games = int(draft_df[col].sum())
                if games < 30:
                    continue
                wr = draft_df[draft_df[col] == 1]["blue_wins"].mean()
                champ_wr.append({"champion": champ, "wr_blue": round(wr * 100, 1), "games": games})
            champ_wr_df = pd.DataFrame(champ_wr).sort_values("wr_blue", ascending=False)

            col_top_champ, col_bot_champ = st.columns(2)
            with col_top_champ:
                top_champs = champ_wr_df.head(8)
                fig, ax = plt.subplots(figsize=(5, 3.5), facecolor="#070b14")
                ax.set_facecolor("#0d1117")
                for s in ax.spines.values(): s.set_color("#1e2a3a")
                ax.barh(top_champs["champion"].values[::-1], top_champs["wr_blue"].values[::-1],
                        color="#0bc4e3", alpha=0.85)
                ax.axvline(50, color="#c89b3c", linestyle="--", linewidth=1)
                ax.set_xlim(45, 68)
                ax.set_title("Champions les plus forts (WR blue ≥ 30 games)", color="#0bc4e3",
                             fontsize=9, fontweight="bold")
                ax.tick_params(colors="#8a8070", labelsize=8)
                for bar, val in zip(ax.patches, top_champs["wr_blue"].values[::-1]):
                    ax.text(val + 0.2, bar.get_y() + bar.get_height()/2,
                            f"{val:.1f}%", va="center", color="white", fontsize=7)
                plt.tight_layout()
                st.pyplot(fig)
                plt.close()

            with col_bot_champ:
                bot_champs = champ_wr_df.tail(8).sort_values("wr_blue")
                fig, ax = plt.subplots(figsize=(5, 3.5), facecolor="#070b14")
                ax.set_facecolor("#0d1117")
                for s in ax.spines.values(): s.set_color("#1e2a3a")
                ax.barh(bot_champs["champion"].values[::-1], bot_champs["wr_blue"].values[::-1],
                        color="#e84057", alpha=0.85)
                ax.axvline(50, color="#c89b3c", linestyle="--", linewidth=1)
                ax.set_xlim(30, 55)
                ax.set_title("Champions les moins performants (WR blue)", color="#e84057",
                             fontsize=9, fontweight="bold")
                ax.tick_params(colors="#8a8070", labelsize=8)
                for bar, val in zip(ax.patches, bot_champs["wr_blue"].values[::-1]):
                    ax.text(val - 0.5, bar.get_y() + bar.get_height()/2,
                            f"{val:.1f}%", va="center", ha="right", color="white", fontsize=7)
                plt.tight_layout()
                st.pyplot(fig)
                plt.close()

            st.caption("""
**Attention** : ce WR est mesuré côté bleu uniquement, et ne contrôle pas pour le skill des joueurs.
Un champion avec WR élevé peut l'être parce qu'il est joué par de meilleurs joueurs, ou parce qu'il
était fort dans la méta au moment de la collecte — pas nécessairement à cause de synergies.
""")
        except Exception:
            pass

    # ── Conclusion ────────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("8. Ce qu'on garde et ce qu'on abandonne")

    col_keep, col_next = st.columns(2)

    with col_keep:
        st.markdown("### ✅ Ce qu'on garde")
        st.markdown("""
**Approche statistique pour l'app web** :
- Win rates de paires (11 357 paires observées)
- Pénalité off-meta par rôle
- Interprétable, rapide, pas de modèle à maintenir

**Le modèle ML draft comme résultat de recherche** :
- AUC 0.51 est une vraie information : le draft n'est pas le facteur principal
- Les WR individuels par champion donnent une tier list implicite
""")

    with col_next:
        st.markdown("### 🔭 Ce qu'il faudrait pour vraiment l'améliorer")
        st.markdown("""
**1. Plus de données** : 100k+ matchs par champion → réduire le bruit

**2. Features de composition typologiques** :
- % engage vs % poke vs % burst
- Portée moyenne (range vs melee)
- Damage type diversity (AD/AP/mix)
→ Généralise sans avoir besoin de chaque paire spécifique

**3. Isoler le draft du skill** :
- Entraîner sur des matchs de même elo exact
- Ou utiliser des données pro (LCS/LEC où les joueurs ont un niveau homogène)

**4. Champion embeddings** :
- Word2Vec sur les 10k matchs → embeddings 64D
- Cosine similarity capture les synergies latentes sans données par paire
""")

    st.info("""
**Conclusion** : Prédire l'issue d'une game à partir du draft seul est un problème **fondamentalement limité**
par le bruit du skill individuel en solo queue (AUC plafond théorique ≈ 0.55–0.60).
Notre XGBoost game-state (AUC 0.857) fonctionne bien car il voit **ce qui se passe en jeu**,
pas juste qui a été sélectionné. C'est là la vraie information prédictive.
""")
