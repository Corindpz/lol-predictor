"""FastAPI backend — sert les prédictions et les analyses post-game."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.data.fetch_player import (
    build_game_summary,
    extract_full_timeline,
    get_match_info,
    get_match_timeline,
    get_puuid,
    get_recent_matches,
)
from src.models.predict import predict_win_probability, get_advice
from src.features.build_features import FEATURE_COLS

import joblib
import numpy as np
import pandas as pd

app = FastAPI(title="LoL Win Predictor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Chargement modèle + SHAP au démarrage
_model = None
_scaler = None
_shap_explainer = None

def _load_model():
    global _model, _scaler, _shap_explainer
    import shap
    _model = joblib.load("models/xgboost_final.pkl")
    if Path("models/scaler.pkl").exists():
        _scaler = joblib.load("models/scaler.pkl")
    base = _model.calibrated_classifiers_[0].estimator
    _shap_explainer = shap.TreeExplainer(base)

@app.on_event("startup")
def startup():
    _load_model()


class FeatureInput(BaseModel):
    kills_diff: float = 0
    deaths_diff: float = 0
    cs_diff: float = 0
    gold_diff: float = 0
    level_diff: float = 0
    towers_diff: float = 0
    dragons_diff: float = 0
    heralds_diff: float = 0
    barons_diff: float = 0
    kills_last_3min: float = 0
    game_time_minutes: float = 20


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predict")
def predict(features: FeatureInput):
    f = features.model_dump()
    proba = predict_win_probability(f)
    advice = get_advice(f, proba)

    # SHAP — contribution de chaque feature en delta de probabilité
    import shap
    X = pd.DataFrame([f])[FEATURE_COLS]
    shap_vals = _shap_explainer.shap_values(X)
    # shap_vals shape: (1, n_features) ou (2, 1, n_features) selon version
    if isinstance(shap_vals, list):
        sv = shap_vals[1][0]  # classe 1 (victoire)
    else:
        sv = shap_vals[0]

    # Convertir log-odds SHAP en delta probabilité approximatif
    base_log_odds = np.log(0.5 / 0.5)  # prior 50/50
    feature_impacts = {}
    for feat, sv_val in zip(FEATURE_COLS, sv):
        # delta prob = sigmoid(base + sv) - sigmoid(base)
        delta = float(1 / (1 + np.exp(-(base_log_odds + sv_val))) - 0.5)
        feature_impacts[feat] = round(delta * 100, 2)  # en %

    return {
        "blue_win_probability": round(proba * 100, 1),
        "advice": advice,
        "feature_impacts": feature_impacts,
    }


@app.get("/player/{riot_id}")
def get_player(riot_id: str):
    """riot_id = 'GameName-TAG' (tiret comme séparateur dans l'URL)"""
    if "-" not in riot_id:
        raise HTTPException(400, "Format invalide — utilisez GameName-TAG")
    parts = riot_id.rsplit("-", 1)
    game_name, tag = parts[0], parts[1]

    puuid = get_puuid(game_name, tag)
    if not puuid:
        raise HTTPException(404, f"Joueur {riot_id} introuvable")

    match_ids = get_recent_matches(puuid, count=10)
    games = []
    for mid in match_ids:
        info = get_match_info(mid)
        if not info:
            continue
        if info["info"].get("gameDuration", 0) < 15 * 60:
            continue
        summary = build_game_summary(info, puuid)
        if summary:
            games.append(summary)

    return {"puuid": puuid, "riot_id": riot_id, "games": games}


@app.get("/game/{match_id}")
def get_game(match_id: str, player_team: str = "blue"):
    info = get_match_info(match_id)
    timeline = get_match_timeline(match_id)
    if not info or not timeline:
        raise HTTPException(404, "Partie introuvable")

    game_data = extract_full_timeline(timeline, info)
    features_by_min = game_data["features_by_min"]
    key_events = game_data["key_events"]
    blue_won = game_data["blue_won"]

    # Courbe de probabilité minute par minute
    curve = []
    for snap in features_by_min:
        if snap["minute"] < 3:
            continue
        p_blue = predict_win_probability(snap)
        p_player = p_blue if player_team == "blue" else 1 - p_blue
        curve.append({
            "minute": snap["minute"],
            "blue_win_prob": round(p_blue * 100, 1),
            "player_win_prob": round(p_player * 100, 1),
            "gold_diff": snap["gold_diff"],
            "kills_diff": snap["kills_diff"],
        })

    # Analyse "qui est fautif / qui a carry"
    blame = _compute_blame(timeline, info, blue_won)

    return {
        "match_id": match_id,
        "blue_won": blue_won,
        "duration_min": round(info["info"].get("gameDuration", 0) / 60, 1),
        "curve": curve,
        "key_events": key_events[:20],
        "blame": blame,
    }


def _compute_blame(timeline: dict, info: dict, blue_won: bool) -> list[dict]:
    """Score d'impact individuel par joueur."""
    participants = {p["participantId"]: p for p in info["info"]["participants"]}
    frames = timeline.get("info", {}).get("frames", [])

    # Accumulateurs par joueur
    stats = {pid: {
        "kills": 0, "deaths": 0, "assists": 0,
        "wards_placed": 0, "wards_killed": 0,
        "name": participants.get(pid, {}).get("summonerName", f"P{pid}"),
        "champion": participants.get(pid, {}).get("championName", "?"),
        "team": "blue" if pid <= 5 else "red",
        "won": participants.get(pid, {}).get("win", False),
        "cs": 0, "gold": 0,
    } for pid in range(1, 11)}

    team_kills = {"blue": 0, "red": 0}

    for frame in frames:
        # Stats à la dernière frame
        for pid_str, pf in frame.get("participantFrames", {}).items():
            pid = int(pid_str)
            if pid not in stats:
                continue
            cs = pf.get("minionsKilled", 0) + pf.get("jungleMinionsKilled", 0)
            stats[pid]["cs"] = cs
            stats[pid]["gold"] = pf.get("totalGold", 0)

        for event in frame.get("events", []):
            etype = event.get("type")
            if etype == "CHAMPION_KILL":
                killer = event.get("killerId", 0)
                victim = event.get("victimId", 0)
                assists = event.get("assistingParticipantIds", [])
                if killer in stats:
                    stats[killer]["kills"] += 1
                    team_kills[stats[killer]["team"]] += 1
                if victim in stats:
                    stats[victim]["deaths"] += 1
                for a in assists:
                    if a in stats:
                        stats[a]["assists"] += 1
            elif etype == "WARD_PLACED":
                creator = event.get("creatorId", 0)
                if creator in stats:
                    stats[creator]["wards_placed"] += 1
            elif etype == "WARD_KILL":
                killer = event.get("killerId", 0)
                if killer in stats:
                    stats[killer]["wards_killed"] += 1

    result = []
    for pid, s in stats.items():
        team = s["team"]
        team_k = team_kills.get(team, 1) or 1
        kp = round((s["kills"] + s["assists"]) / team_k * 100)
        # Score impact : kill participation + vision - deaths penalty
        vision_score = s["wards_placed"] * 1.5 + s["wards_killed"] * 2
        impact = kp * 0.5 + vision_score * 0.3 - s["deaths"] * 3
        result.append({
            "pid": pid,
            "name": s["name"],
            "champion": s["champion"],
            "team": team,
            "won": s["won"],
            "kills": s["kills"],
            "deaths": s["deaths"],
            "assists": s["assists"],
            "kda_str": f"{s['kills']}/{s['deaths']}/{s['assists']}",
            "kill_participation": kp,
            "wards_placed": s["wards_placed"],
            "wards_killed": s["wards_killed"],
            "cs": s["cs"],
            "gold": s["gold"],
            "impact_score": round(impact, 1),
        })

    # Tri : les plus impactants en premier, séparés par équipe
    result.sort(key=lambda x: x["impact_score"], reverse=True)
    return result
