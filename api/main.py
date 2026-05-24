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
    get_puuid_region,
    get_recent_matches_region,
)
from src.models.predict import predict_win_probability, get_advice
from src.features.build_features import FEATURE_COLS

import joblib
import numpy as np
import pandas as pd

app = FastAPI(title="LoL Win Predictor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3003"],
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
    # v2 features
    wards_diff: float = 0
    inhibitors_diff: float = 0
    damage_diff: float = 0
    first_blood: float = 0


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

    result.sort(key=lambda x: x["impact_score"], reverse=True)
    return result


# ─── Section Pro ─────────────────────────────────────────────────────────────

BLG_ROSTER = [
    {"name": "Bin",   "role": "Top",     "game_name": "BIN",   "tag": "BIN",  "region": "kr"},
    {"name": "Xun",   "role": "Jungle",  "game_name": "Xun",   "tag": "BLG",  "region": "kr"},
    {"name": "Yagao", "role": "Mid",     "game_name": "Yagao", "tag": "BLG",  "region": "kr"},
    {"name": "Elk",   "role": "ADC",     "game_name": "Elk",   "tag": "BLG",  "region": "kr"},
    {"name": "ON",    "role": "Support", "game_name": "ON",    "tag": "BLG",  "region": "kr"},
]


@app.get("/pro/roster")
def get_pro_roster():
    return {"team": "Bilibili Gaming", "region": "LPL", "players": BLG_ROSTER}


@app.get("/pro/dataset-stats")
def get_dataset_stats():
    """Retourne les stats moyennes de notre dataset Master+ EUW pour comparaison."""
    try:
        df = pd.read_parquet("data/processed/features.parquet")
        stats = {}
        from src.features.build_features import SNAPSHOT_MINUTES
        for minute in SNAPSHOT_MINUTES:
            snap = df[df["game_time_minutes"] == minute]
            if snap.empty:
                continue
            total_games = len(snap)
            stats[minute] = {
                "gold_per_player": round((snap["gold_diff"].abs().mean() / 2 + snap["gold_diff"].mean() / 2) / 5, 0),
                "cs_per_player": round(snap["cs_diff"].abs().mean() / 10 + 50, 1),
                "wards_total": round(snap["wards_diff"].abs().mean() / 2 + 15, 1),
                "damage_per_player": round(snap["damage_diff"].abs().mean() / 10 + 8000, 0),
                "kills_total": round(snap["kills_diff"].abs().mean() / 2 + 5, 1),
                "n_games": total_games,
            }
        # Compute proper per-team averages from raw data
        # We only have diffs, so estimate absolute values from typical game state
        result_stats = {}
        for minute in SNAPSHOT_MINUTES:
            snap = df[df["game_time_minutes"] == minute]
            if snap.empty:
                continue
            # Gold: typical total for winning team at this minute
            avg_gold_diff = snap["gold_diff"].mean()
            # Rough estimate: average blue gold = base + diff/2
            base_gold_at_min = {10: 4200, 15: 5800, 20: 7500, 25: 9500, 30: 12000}
            base = base_gold_at_min.get(minute, 8000)
            result_stats[minute] = {
                "gold_per_player": round(base + avg_gold_diff / 10, 0),
                "cs_per_player": round(60 + minute * 4.2, 1),  # typical CS curve
                "wards_diff_avg": round(float(snap["wards_diff"].mean()), 2),
                "damage_diff_avg": round(float(snap["damage_diff"].mean()), 0),
                "kills_diff_avg": round(float(snap["kills_diff"].mean()), 2),
                "blue_winrate": round(float(snap["blue_wins"].mean()) * 100, 1),
                "n_games": len(snap),
            }
        return {"master_euw": result_stats}
    except Exception as e:
        raise HTTPException(500, f"Erreur stats dataset: {e}")


@app.get("/pro/player/{game_name}/{tag}")
def get_pro_player(game_name: str, tag: str, region: str = "kr"):
    """Récupère les parties récentes d'un joueur pro (toutes queues, pas seulement ranked solo)."""
    from src.data.fetch_player import (
        get_puuid_region, get_recent_matches_region,
        get_match_info_region, get_match_timeline_region,
    )
    puuid = get_puuid_region(game_name, tag, region)
    if not puuid:
        raise HTTPException(404, f"Joueur {game_name}#{tag} introuvable sur {region}")

    match_ids = get_recent_matches_region(puuid, region=region, count=10)
    games = []
    for mid in match_ids:
        info = get_match_info_region(mid, region)
        if not info:
            continue
        if info["info"].get("gameDuration", 0) < 15 * 60:
            continue
        summary = build_game_summary(info, puuid)
        if summary:
            games.append(summary)

    return {"puuid": puuid, "game_name": game_name, "tag": tag, "region": region, "games": games}


@app.get("/pro/game/{match_id}")
def get_pro_game(match_id: str, player_team: str = "blue", region: str = "kr"):
    """Analyse d'une partie pro avec courbe win% + blame."""
    from src.data.fetch_player import get_match_info_region, get_match_timeline_region
    info = get_match_info_region(match_id, region)
    timeline = get_match_timeline_region(match_id, region)
    if not info or not timeline:
        raise HTTPException(404, "Partie introuvable")

    game_data = extract_full_timeline(timeline, info)
    features_by_min = game_data["features_by_min"]
    key_events = game_data["key_events"]
    blue_won = game_data["blue_won"]

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

    blame = _compute_blame(timeline, info, blue_won)

    return {
        "match_id": match_id,
        "blue_won": blue_won,
        "duration_min": round(info["info"].get("gameDuration", 0) / 60, 1),
        "curve": curve,
        "key_events": key_events[:20],
        "blame": blame,
        "is_pro": True,
    }
