"""
Explications par prédiction via SHAP (TreeExplainer sur l'XGBoost de base).

Pour un snapshot donné, renvoie les features qui poussent le plus la probabilité
vers l'équipe bleue ou rouge, avec une formulation lisible pour l'UX.
"""

import json
from pathlib import Path

import joblib
import pandas as pd

from src.features.build_features import FEATURE_COLS

# Libellés lisibles (affichage) pour chaque feature.
FEATURE_LABELS = {
    "gold_diff": "Écart d'or",
    "gold_slope": "Momentum économique",
    "current_gold_diff": "Or disponible",
    "level_diff": "Écart de niveaux",
    "cs_diff": "Écart de farm (CS)",
    "kills_diff": "Écart de kills",
    "kills_last_3min": "Momentum de kills (3 min)",
    "damage_diff": "Écart de dégâts",
    "players_alive_diff": "Joueurs vivants",
    "first_blood": "First Blood",
    "towers_diff": "Écart de tours",
    "plates_diff": "Écart de plaques",
    "inhibitors_diff": "Écart d'inhibiteurs",
    "first_tower": "Première tour",
    "dragons_diff": "Écart de dragons",
    "dragon_soul": "Âme du dragon",
    "heralds_diff": "Écart de Hérauts",
    "barons_diff": "Barons pris",
    "baron_active": "Buff Baron actif",
    "elder_active": "Dragon Ancestral actif",
    "void_grubs_diff": "Nuisibles du Néant",
    "game_time_minutes": "Temps de jeu",
}

_explainer = None
_base_model = None


def _unwrap_base(model):
    """Récupère l'XGBoost sous-jacent depuis le CalibratedClassifierCV/FrozenEstimator."""
    if hasattr(model, "calibrated_classifiers_"):
        est = model.calibrated_classifiers_[0].estimator
        return getattr(est, "estimator", est)
    return getattr(model, "estimator", model)


def _load():
    global _explainer, _base_model
    import shap

    model_path = Path("models/xgboost_final.pkl")
    if not model_path.exists():
        raise FileNotFoundError("Modèle introuvable. Lance src/models/train.py d'abord.")

    model = joblib.load(model_path)
    _base_model = _unwrap_base(model)
    _explainer = shap.TreeExplainer(_base_model)


def explain_prediction(features: dict, top_k: int = 5) -> list[dict]:
    """Top contributions à la prédiction pour un snapshot.

    Retour : liste triée par impact décroissant, chaque item =
        {feature, label, value, contribution, favors}
    contribution > 0 pousse vers l'équipe bleue, < 0 vers la rouge.
    """
    global _explainer
    if _explainer is None:
        _load()

    X = pd.DataFrame([features]).reindex(columns=FEATURE_COLS, fill_value=0)
    shap_values = _explainer.shap_values(X)[0]

    rows = []
    for col, val, contrib in zip(FEATURE_COLS, X.iloc[0].tolist(), shap_values):
        rows.append({
            "feature": col,
            "label": FEATURE_LABELS.get(col, col),
            "value": round(float(val), 1),
            "contribution": round(float(contrib), 3),
            "favors": "blue" if contrib > 0 else "red",
        })
    rows.sort(key=lambda r: abs(r["contribution"]), reverse=True)
    return rows[:top_k]


if __name__ == "__main__":
    # Démo : explique un snapshot fictif d'avance bleue.
    demo = {"gold_diff": 4000, "level_diff": 4, "dragons_diff": 2,
            "towers_diff": 3, "kills_diff": 5, "game_time_minutes": 20}
    for r in explain_prediction(demo):
        print(json.dumps(r, ensure_ascii=False))
