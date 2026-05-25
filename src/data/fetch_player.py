"""
Récupère les données d'un joueur et de ses parties récentes depuis la Riot API.
Format Riot ID : "GameName#TAG" (ex: "Faker#T1", "Caps#EUW")
"""

import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("RIOT_API_KEY")
REGION = os.getenv("REGION", "euw1")
MATCH_REGION = os.getenv("MATCH_REGION", "europe")
HEADERS = {"X-Riot-Token": API_KEY}

CACHE_DIR = Path("data/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

BLUE_IDS = {1, 2, 3, 4, 5}
RED_IDS  = {6, 7, 8, 9, 10}

DRAGON_LABELS = {
    "FIRE_DRAGON":     "Dragon Infernal",
    "EARTH_DRAGON":    "Dragon Montagne",
    "WATER_DRAGON":    "Dragon Océan",
    "AIR_DRAGON":      "Dragon Nuage",
    "HEXTECH_DRAGON":  "Dragon Hextech",
    "CHEMTECH_DRAGON": "Dragon Chemtech",
    "ELDER_DRAGON":    "Ancien Dragon",
}

TOWER_TYPES = {
    "OUTER_TURRET": "Tour extérieure",
    "INNER_TURRET": "Tour intérieure",
    "BASE_TURRET":  "Tour de base",
    "NEXUS_TURRET": "Tour du Nexus",
}

LANE_LABELS = {
    "TOP_LANE": "Top",
    "MID_LANE": "Mid",
    "BOT_LANE": "Bot",
}


def _get(url: str, params: dict = None, retries: int = 3):
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, params=params, timeout=10)
        except requests.exceptions.RequestException:
            time.sleep(2 ** attempt)
            continue
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 429:
            time.sleep(int(resp.headers.get("Retry-After", 10)))
        elif resp.status_code == 404:
            return None
        else:
            time.sleep(2 ** attempt)
    return None


ROUTING = {
    "euw": {"account": "europe", "match": "europe"},
    "kr":  {"account": "asia",   "match": "asia"},
    "na":  {"account": "americas", "match": "americas"},
    "br":  {"account": "americas", "match": "americas"},
}


def get_puuid(game_name: str, tag_line: str) -> str | None:
    url = f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
    data = _get(url)
    return data["puuid"] if data else None


def get_puuid_region(game_name: str, tag_line: str, region: str = "euw") -> str | None:
    routing = ROUTING.get(region, ROUTING["euw"])
    url = f"https://{routing['account']}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
    data = _get(url)
    return data["puuid"] if data else None


def get_recent_matches(puuid: str, count: int = 10) -> list[str]:
    url = f"https://{MATCH_REGION}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
    return _get(url, params={"queue": 420, "count": count}) or []


def get_recent_matches_region(puuid: str, region: str = "euw", count: int = 10) -> list[str]:
    routing = ROUTING.get(region, ROUTING["euw"])
    url = f"https://{routing['match']}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
    return _get(url, params={"count": count}) or []


def get_match_info_region(match_id: str, region: str = "euw") -> dict | None:
    cache = CACHE_DIR / f"{match_id}_info.json"
    if cache.exists():
        return json.loads(cache.read_text())
    routing = ROUTING.get(region, ROUTING["euw"])
    data = _get(f"https://{routing['match']}.api.riotgames.com/lol/match/v5/matches/{match_id}")
    if data:
        cache.write_text(json.dumps(data))
    return data


def get_match_timeline_region(match_id: str, region: str = "euw") -> dict | None:
    cache = CACHE_DIR / f"{match_id}_timeline.json"
    if cache.exists():
        return json.loads(cache.read_text())
    routing = ROUTING.get(region, ROUTING["euw"])
    data = _get(f"https://{routing['match']}.api.riotgames.com/lol/match/v5/matches/{match_id}/timeline")
    if data:
        cache.write_text(json.dumps(data))
    return data


def get_match_info(match_id: str) -> dict | None:
    cache = CACHE_DIR / f"{match_id}_info.json"
    if cache.exists():
        return json.loads(cache.read_text())
    data = _get(f"https://{MATCH_REGION}.api.riotgames.com/lol/match/v5/matches/{match_id}")
    if data:
        cache.write_text(json.dumps(data))
    return data


def get_match_timeline(match_id: str) -> dict | None:
    cache = CACHE_DIR / f"{match_id}_timeline.json"
    if cache.exists():
        return json.loads(cache.read_text())
    data = _get(f"https://{MATCH_REGION}.api.riotgames.com/lol/match/v5/matches/{match_id}/timeline")
    if data:
        cache.write_text(json.dumps(data))
    return data


def get_player_team(info: dict, puuid: str) -> str:
    for p in info.get("info", {}).get("participants", []):
        if p.get("puuid") == puuid:
            return "blue" if p.get("teamId") == 100 else "red"
    return "blue"


def build_game_summary(info: dict, puuid: str) -> dict:
    for p in info.get("info", {}).get("participants", []):
        if p.get("puuid") != puuid:
            continue
        return {
            "match_id": info["metadata"]["matchId"],
            "champion": p.get("championName", "?"),
            "role": p.get("teamPosition", "?"),
            "kills": p.get("kills", 0),
            "deaths": p.get("deaths", 0),
            "assists": p.get("assists", 0),
            "won": p.get("win", False),
            "duration_min": round(info["info"].get("gameDuration", 0) / 60, 1),
            "game_creation": info["info"].get("gameCreation", 0),
            "player_team": get_player_team(info, puuid),
        }
    return {}


def _detect_teamfights(kills: list[tuple]) -> list[dict]:
    """Détecte les teamfights : clusters de 3+ kills en moins de 30 secondes."""
    if len(kills) < 3:
        return []

    kills_sorted = sorted(kills, key=lambda x: x[0])
    events = []
    used: set[int] = set()

    for i, (ts, team) in enumerate(kills_sorted):
        if i in used:
            continue
        cluster_idx = [
            j for j, (t2, _) in enumerate(kills_sorted)
            if abs(t2 - ts) <= 30 and j not in used
        ]
        if len(cluster_idx) >= 3:
            cluster = [kills_sorted[j] for j in cluster_idx]
            blue_k = sum(1 for _, t in cluster if t == "blue")
            red_k  = sum(1 for _, t in cluster if t == "red")
            winner = "blue" if blue_k >= red_k else "red"
            events.append({
                "min": round(ts / 60, 1),
                "label": f"Teamfight — {blue_k + red_k} kills",
                "team": winner,
                "type": "teamfight",
            })
            for j in cluster_idx:
                used.add(j)

    return events


def extract_full_timeline(timeline: dict, info: dict) -> dict:
    frames = timeline.get("info", {}).get("frames", [])

    blue_won = False
    for team in info.get("info", {}).get("teams", []):
        if team["teamId"] == 100:
            blue_won = team["win"]

    features_by_min = []
    key_events = []
    all_kills: list[tuple] = []  # (timestamp_sec, team_str)

    kills_blue = kills_red = 0
    deaths_blue = deaths_red = 0
    towers_blue = towers_red = 0
    inhibitors_blue = inhibitors_red = 0
    dragons_blue = dragons_red = 0
    heralds_blue = heralds_red = 0
    barons_blue = barons_red = 0
    wards_blue = wards_red = 0
    plates_blue = plates_red = 0
    kills_blue_window: list[float] = []
    first_blood = 0
    dragon_soul = 0
    first_blood_done = False

    for frame_idx, frame in enumerate(frames):
        pf = frame.get("participantFrames", {})

        blue_cs = blue_gold = blue_level = blue_damage = blue_xp = blue_cur_gold = blue_cc = 0
        red_cs  = red_gold  = red_level  = red_damage  = red_xp  = red_cur_gold  = red_cc  = 0

        for pid_str, stats in pf.items():
            pid = int(pid_str)
            cs  = stats.get("minionsKilled", 0) + stats.get("jungleMinionsKilled", 0)
            gold = stats.get("totalGold", 0)
            lv   = stats.get("level", 0)
            dmg  = stats.get("damageStats", {}).get("totalDamageDoneToChampions", 0)
            xp   = stats.get("xp", 0)
            cg   = stats.get("currentGold", 0)
            cc   = stats.get("timeEnemySpentControlled", 0)
            if pid in BLUE_IDS:
                blue_cs += cs; blue_gold += gold; blue_level += lv; blue_damage += dmg
                blue_xp += xp; blue_cur_gold += cg; blue_cc += cc
            else:
                red_cs += cs; red_gold += gold; red_level += lv; red_damage += dmg
                red_xp += xp; red_cur_gold += cg; red_cc += cc

        current_time_sec = frame_idx * 60

        for event in frame.get("events", []):
            etype = event.get("type")
            ts    = event.get("timestamp", 0) / 1000
            min_  = round(ts / 60, 1)
            killer_team = event.get("killerTeamId", event.get("teamId", 0))

            if etype == "CHAMPION_KILL":
                killer_id = event.get("killerId", 0)
                victim_id = event.get("victimId", 0)

                if killer_id in BLUE_IDS:
                    kills_blue += 1
                    kills_blue_window.append(ts)
                    all_kills.append((ts, "blue"))
                    if not first_blood_done:
                        first_blood = 1
                        first_blood_done = True
                        key_events.append({"min": min_, "label": "First Blood", "team": "blue", "type": "first_blood"})
                elif killer_id in RED_IDS:
                    kills_red += 1
                    all_kills.append((ts, "red"))
                    if not first_blood_done:
                        first_blood = -1
                        first_blood_done = True
                        key_events.append({"min": min_, "label": "First Blood", "team": "red", "type": "first_blood"})

                if victim_id in BLUE_IDS:
                    deaths_blue += 1
                elif victim_id in RED_IDS:
                    deaths_red += 1

            elif etype == "BUILDING_KILL":
                btype = event.get("buildingType", "")
                lane  = LANE_LABELS.get(event.get("laneType", ""), "")

                if btype == "INHIBITOR_BUILDING":
                    if killer_team == 100:
                        inhibitors_blue += 1
                        key_events.append({"min": min_, "label": f"Inhibiteur {lane}", "team": "blue", "type": "inhibitor"})
                    else:
                        inhibitors_red += 1
                        key_events.append({"min": min_, "label": f"Inhibiteur {lane}", "team": "red", "type": "inhibitor"})
                else:
                    tower_label = TOWER_TYPES.get(event.get("towerType", ""), "Tour")
                    label = f"{tower_label} {lane}".strip()
                    if killer_team == 100:
                        towers_blue += 1
                        key_events.append({"min": min_, "label": label, "team": "blue", "type": "tower"})
                    else:
                        towers_red += 1
                        key_events.append({"min": min_, "label": label, "team": "red", "type": "tower"})

            elif etype == "ELITE_MONSTER_KILL":
                monster = event.get("monsterType", "")
                subtype = event.get("monsterSubType", "")

                if monster == "DRAGON":
                    is_elder = subtype == "ELDER_DRAGON"
                    dragon_name = DRAGON_LABELS.get(subtype, "Dragon")
                    event_type = "elder_dragon" if is_elder else "dragon"

                    if killer_team == 100:
                        dragons_blue += 1
                        key_events.append({"min": min_, "label": dragon_name, "team": "blue", "type": event_type})
                    else:
                        dragons_red += 1
                        key_events.append({"min": min_, "label": dragon_name, "team": "red", "type": event_type})

                elif monster == "BARON_NASHOR":
                    if killer_team == 100:
                        barons_blue += 1
                        key_events.append({"min": min_, "label": "Baron Nashor", "team": "blue", "type": "baron"})
                    else:
                        barons_red += 1
                        key_events.append({"min": min_, "label": "Baron Nashor", "team": "red", "type": "baron"})

                elif monster == "RIFTHERALD":
                    if killer_team == 100:
                        heralds_blue += 1
                        key_events.append({"min": min_, "label": "Rift Herald", "team": "blue", "type": "rift_herald"})
                    else:
                        heralds_red += 1
                        key_events.append({"min": min_, "label": "Rift Herald", "team": "red", "type": "rift_herald"})

                elif monster == "HORDE":  # Void Grubs
                    if killer_team == 100:
                        key_events.append({"min": min_, "label": "Void Grub", "team": "blue", "type": "void_grub"})
                    else:
                        key_events.append({"min": min_, "label": "Void Grub", "team": "red", "type": "void_grub"})

            elif etype == "WARD_PLACED":
                creator = event.get("creatorId", 0)
                if creator in BLUE_IDS:
                    wards_blue += 1
                elif creator in RED_IDS:
                    wards_red += 1

            elif etype == "TURRET_PLATE_DESTROYED":
                plate_team = event.get("teamId", 0)
                if plate_team == 100:
                    plates_red += 1
                else:
                    plates_blue += 1

            elif etype == "DRAGON_SOUL_GIVEN":
                soul_team = event.get("teamId", 0)
                dragon_soul = 1 if soul_team == 100 else -1
                team_str = "blue" if soul_team == 100 else "red"
                key_events.append({"min": min_, "label": "Dragon Soul", "team": team_str, "type": "dragon_soul"})

        kills_blue_recent = sum(1 for t in kills_blue_window if t >= current_time_sec - 180)

        features_by_min.append({
            "minute": frame_idx,
            "kills_diff": kills_blue - kills_red,
            "deaths_diff": deaths_blue - deaths_red,
            "cs_diff": blue_cs - red_cs,
            "gold_diff": blue_gold - red_gold,
            "level_diff": blue_level - red_level,
            "towers_diff": towers_blue - towers_red,
            "dragons_diff": dragons_blue - dragons_red,
            "heralds_diff": heralds_blue - heralds_red,
            "barons_diff": barons_blue - barons_red,
            "kills_last_3min": kills_blue_recent,
            "game_time_minutes": frame_idx,
            "wards_diff": wards_blue - wards_red,
            "inhibitors_diff": inhibitors_blue - inhibitors_red,
            "damage_diff": blue_damage - red_damage,
            "first_blood": first_blood,
            "xp_diff": blue_xp - red_xp,
            "plates_diff": plates_blue - plates_red,
            "current_gold_diff": blue_cur_gold - red_cur_gold,
            "dragon_soul": dragon_soul,
            "cc_diff": blue_cc - red_cc,
        })

    # Teamfight detection — post-process sur tous les kills
    teamfight_events = _detect_teamfights(all_kills)
    key_events.extend(teamfight_events)
    key_events.sort(key=lambda e: e["min"])

    return {
        "features_by_min": features_by_min,
        "key_events": key_events,
        "blue_won": blue_won,
    }
