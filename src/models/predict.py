"""Charge le modèle entraîné et retourne une probabilité de victoire."""

from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from src.features.build_features import FEATURE_COLS

_model = None
_scaler = None


def _load():
    global _model, _scaler
    model_path = Path("models/xgboost_final.pkl")
    scaler_path = Path("models/scaler.pkl")

    if not model_path.exists():
        raise FileNotFoundError("Modèle introuvable. Lance src/models/train.py d'abord.")

    _model = joblib.load(model_path)
    _scaler = joblib.load(scaler_path) if scaler_path.exists() else None


def predict_win_probability(features: dict) -> float:
    """
    features : dict avec les clés de FEATURE_COLS
    Retourne la probabilité de victoire de l'équipe bleue (0.0 → 1.0)
    """
    global _model, _scaler
    if _model is None:
        _load()

    X = pd.DataFrame([features])[FEATURE_COLS]

    # XGBoost calibré n'a pas besoin du scaler — LogReg oui
    # On laisse le modèle gérer (XGBoost ignore les features non-scaled)
    proba = _model.predict_proba(X)[0][1]
    return float(np.clip(proba, 0.01, 0.99))


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
