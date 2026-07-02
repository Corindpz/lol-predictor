"""
Wrapper pour la Live Client Data API de League of Legends.
URL locale : https://127.0.0.1:2999/liveclientdata/allgamedata

La Live Client API utilise un certificat auto-signé → verify=False requis.
"""

import warnings
from typing import Optional

import requests
import urllib3

from src.features.build_features import FEATURE_COLS

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

LIVE_CLIENT_URL = "https://127.0.0.1:2999/liveclientdata/allgamedata"

BLUE_TEAM = "ORDER"
RED_TEAM = "CHAOS"


def fetch_live_state() -> Optional[dict]:
    """Retourne le JSON brut de la partie en cours, ou None si hors partie."""
    try:
        resp = requests.get(LIVE_CLIENT_URL, verify=False, timeout=3)
        if resp.status_code == 200:
            return resp.json()
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        pass
    return None


def _aggregate_team(players: list[dict], team: str) -> dict:
    kills = deaths = cs = gold = level = 0
    for p in players:
        if p.get("team") != team:
            continue
        s = p.get("scores", {})
        kills += s.get("kills", 0)
        deaths += s.get("deaths", 0)
        cs += s.get("creepScore", 0)
        level += p.get("level", 1)
        # Gold pas directement dispo dans Live Client API → on l'estime via CS + kills
        # La Live Client API ne donne pas le gold total par joueur
        gold += s.get("kills", 0) * 300 + s.get("assists", 0) * 150 + s.get("creepScore", 0) * 20

    return {"kills": kills, "deaths": deaths, "cs": cs, "gold": gold, "level": level}


def _count_objectives(events: list[dict], team_tag: str) -> dict:
    """Compte les objectifs à partir des events Live Client API."""
    towers = dragons = barons = heralds = 0
    killer_map = {"ORDER": "T1", "CHAOS": "T2"}
    tag = killer_map.get(team_tag, "")

    for event in events:
        etype = event.get("EventName", "")
        result_str = event.get("Result", "")

        if etype == "TurretKilled" and tag in event.get("KillerName", ""):
            towers += 1
        elif etype == "DragonKill" and event.get("Stolen", False) is False:
            if event.get("TurretKillerTeam", event.get("DragonType", "")) != "":
                # attribuer selon le tueur
                killer = event.get("KillerName", "")
                if team_tag == "ORDER" and "_T1_" in killer or killer.startswith("T1"):
                    dragons += 1
                elif team_tag == "CHAOS" and "_T2_" in killer or killer.startswith("T2"):
                    dragons += 1
        elif etype == "BaronKill":
            killer = event.get("KillerName", "")
            if team_tag == "ORDER" and ("T1" in killer or "ORDER" in killer):
                barons += 1
            elif team_tag == "CHAOS" and ("T2" in killer or "CHAOS" in killer):
                barons += 1
        elif etype == "HeraldKill":
            killer = event.get("KillerName", "")
            if team_tag == "ORDER" and ("T1" in killer or "ORDER" in killer):
                heralds += 1
            elif team_tag == "CHAOS" and ("T2" in killer or "CHAOS" in killer):
                heralds += 1

    return {"towers": towers, "dragons": dragons, "barons": barons, "heralds": heralds}


def extract_features(state: dict) -> Optional[dict]:
    """
    Transforme le JSON de la Live Client API en dict de features.
    Retourne None si les données sont insuffisantes.
    """
    players = state.get("allPlayers", [])
    events_raw = state.get("events", {}).get("Events", [])
    game_data = state.get("gameData", {})

    if not players:
        return None

    game_time_sec = game_data.get("gameTime", 0)
    game_time_min = game_time_sec / 60.0

    blue = _aggregate_team(players, BLUE_TEAM)
    red = _aggregate_team(players, RED_TEAM)

    blue_obj = _count_objectives(events_raw, BLUE_TEAM)
    red_obj = _count_objectives(events_raw, RED_TEAM)

    # Momentum : diff de kills bleu - rouge sur les 3 dernières minutes.
    recent_threshold = game_time_sec - 180

    def recent_kills(team_tag: str) -> int:
        return sum(
            1 for e in events_raw
            if e.get("EventName") == "ChampionKill"
            and e.get("EventTime", 0) >= recent_threshold
            and team_tag in e.get("KillerName", "")
        )

    kills_recent_diff = recent_kills(BLUE_TEAM) - recent_kills(RED_TEAM)

    # Features v6 calculables depuis la Live Client API. Les features non
    # disponibles en live (gold_slope, players_alive_diff, damage_diff, plates,
    # inhibiteurs, buffs, void grubs...) sont mises à 0 par predict.py (reindex).
    return {
        "gold_diff": blue["gold"] - red["gold"],
        "current_gold_diff": 0,
        "level_diff": blue["level"] - red["level"],
        "cs_diff": blue["cs"] - red["cs"],
        "kills_diff": blue["kills"] - red["kills"],
        "kills_last_3min": kills_recent_diff,
        "players_alive_diff": 0,
        "towers_diff": blue_obj["towers"] - red_obj["towers"],
        "dragons_diff": blue_obj["dragons"] - red_obj["dragons"],
        "heralds_diff": blue_obj["heralds"] - red_obj["heralds"],
        "barons_diff": blue_obj["barons"] - red_obj["barons"],
        "game_time_minutes": game_time_min,
    }


def get_current_features() -> Optional[dict]:
    """API publique : retourne les features live ou None si hors partie."""
    state = fetch_live_state()
    if state is None:
        return None
    return extract_features(state)
