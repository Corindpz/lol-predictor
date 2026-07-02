"""Charge le modèle entraîné et retourne une probabilité de victoire."""

import json
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from src.features.build_features import FEATURE_COLS

_model = None


def _load():
    global _model
    model_path = Path("models/xgboost_final.pkl")
    meta_path = Path("models/model_meta.json")

    if not model_path.exists():
        raise FileNotFoundError("Modèle introuvable. Lance src/models/train.py d'abord.")

    _model = joblib.load(model_path)

    # Verifie que le modele servi attend bien les memes features que le code.
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())
        trained_cols = meta.get("feature_cols", [])
        if trained_cols and trained_cols != FEATURE_COLS:
            warnings.warn(
                "Desynchronisation features modele/code : le .pkl a ete entraine "
                f"sur {len(trained_cols)} features, le code en attend {len(FEATURE_COLS)}. "
                "Relance src/models/train.py.",
                RuntimeWarning,
            )


def predict_win_probability(features: dict) -> float:
    """
    features : dict avec les clés de FEATURE_COLS
    Retourne la probabilité de victoire de l'équipe bleue (0.0 → 1.0)
    """
    global _model
    if _model is None:
        _load()

    # reindex : toute feature absente du dict est mise a 0 plutot que de lever
    # une KeyError -> l'inference reste robuste aux chemins de service partiels.
    X = pd.DataFrame([features]).reindex(columns=FEATURE_COLS, fill_value=0)

    # XGBoost calibré est invariant à l'échelle : pas de scaler en inférence.
    proba = _model.predict_proba(X)[0][1]
    return float(np.clip(proba, 0.01, 0.99))


def smooth_probabilities(probs: list[float], alpha: float = 0.3) -> list[float]:
    """Lissage exponentiel (EMA) de la courbe win%.

    Chaque snapshot est predit independamment : sans lissage, le jitter
    minute-a-minute du gold est amplifie en sauts de proba. L'EMA garde le
    signal des vrais objectifs tout en absorbant le bruit. alpha bas = plus lisse.
    """
    if not probs:
        return probs
    out = [probs[0]]
    for p in probs[1:]:
        out.append(alpha * p + (1 - alpha) * out[-1])
    return out


def get_advice(features: dict, proba: float) -> list[str]:
    """Génère 2-3 conseils stratégiques basés sur les écarts de features."""
    advice = []

    if features.get("gold_diff", 0) < -1500:
        advice.append("⚠️ Gros déficit économique — éviter les combats ouverts, farm safe")
    elif features.get("gold_diff", 0) > 2000:
        advice.append("💰 Avantage gold — forcez des objectifs, ne laissez pas le gap se réduire")

    drag = features.get("dragons_diff", 0)
    if drag <= -2:
        advice.append("🐉 L'adversaire contrôle les dragons — priorité sur le prochain spawn")
    elif drag >= 2:
        advice.append("🐉 Vous dominuez les dragons — gardez le contrôle de l'âme")

    if features.get("towers_diff", 0) < -2:
        advice.append("🏰 Plusieurs tours perdues — resserrez votre zone de jeu")

    if features.get("barons_diff", 0) < 0:
        advice.append("⚡ Baron adverse actif — groupez-vous et protégez les structures")

    if features.get("kills_last_3min", 0) >= 3 and proba < 0.5:
        advice.append("🔥 Momentum adverse fort — attendez le CD des compétences clés")

    if not advice:
        if proba > 0.65:
            advice.append("✅ Partie sous contrôle — continuez à sécuriser les objectifs")
        elif proba < 0.35:
            advice.append("⚠️ Situation critique — splitpush ou pick 1v1 pour remonter")
        else:
            advice.append("⚖️ Partie serrée — le prochain objectif majeur sera décisif")

    return advice[:3]
