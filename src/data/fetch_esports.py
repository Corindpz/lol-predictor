"""
Intégration lolesports API — récupère les games pro en tournoi.
Utilise la lolesports esports API (publique) + live stats feed.

Features disponibles depuis live stats :
  gold_diff, kills_diff, cs_diff, level_diff, towers_diff, dragons_diff,
  barons_diff, inhibitors_diff, dragon_soul, first_blood, first_tower,
  infernal_diff, ocean_diff, elder_active
Features non disponibles → défaut 0 :
  wards_diff, damage_diff, xp_diff, plates_diff, current_gold_diff,
  cc_diff, kills_last_3min, heralds_diff, void_grubs_diff, powerspike_diff
"""

import time
from datetime import datetime, timedelta, timezone

import requests

ESPORTS_HEADERS = {"x-api-key": "0TvQnueqKa5mxJntVWt0w4LpLfEkrV1Ta8rQBb9Z"}
ESPORTS_BASE = "https://esports-api.lolesports.com/persisted/gw"
LIVE_BASE = "https://feed.lolesports.com/livestats/v1"

LEAGUE_IDS = {
    "worlds":  "98767975604431411",
    "msi":     "98767991325878492",
    "lec":     "98767991302996019",
    "lck":     "98767991310872058",
    "lcs":     "98767991299243165",
    "lpl":     "98767991314006698",
}

DRAGON_FIRE = {"infernal"}
DRAGON_OCEAN = {"ocean", "water"}


def _esports_get(path: str, params: dict) -> dict:
    params.setdefault("hl", "fr-FR")
    try:
        r = requests.get(f"{ESPORTS_BASE}/{path}", headers=ESPORTS_HEADERS,
                         params=params, timeout=10)
        return r.json() if r.ok else {}
    except Exception:
        return {}


def _live_get(game_id: str, starting_time: str | None = None) -> dict:
    params = {}
    if starting_time:
        params["startingTime"] = starting_time
    try:
        r = requests.get(f"{LIVE_BASE}/window/{game_id}",
                         headers=ESPORTS_HEADERS, params=params, timeout=10)
        return r.json() if (r.ok and r.content) else {}
    except Exception:
        return {}


def get_recent_matches(league: str = "lec", count: int = 10) -> list[dict]:
    """Retourne les derniers matchs terminés pour une league."""
    league_id = LEAGUE_IDS.get(league.lower(), LEAGUE_IDS["lec"])
    data = _esports_get("getSchedule", {"leagueId": league_id})
    events = data.get("data", {}).get("schedule", {}).get("events", [])

    completed = [
        e for e in events
        if e.get("state") == "completed" and e.get("type") == "match"
    ]
    completed.reverse()  # plus récent d'abord

    result = []
    for e in completed[:count]:
        m = e.get("match", {})
        teams = m.get("teams", [])
        winner = next((t["code"] for t in teams if t.get("result", {}).get("outcome") == "win"), "?")
        result.append({
            "match_id":   m.get("id"),
            "date":       e.get("startTime", "")[:10],
            "block":      e.get("blockName", ""),
            "league":     league.upper(),
            "team1":      teams[0].get("code", "?") if len(teams) > 0 else "?",
            "team2":      teams[1].get("code", "?") if len(teams) > 1 else "?",
            "team1_name": teams[0].get("name", "?") if len(teams) > 0 else "?",
            "team2_name": teams[1].get("name", "?") if len(teams) > 1 else "?",
            "team1_img":  teams[0].get("image", "") if len(teams) > 0 else "",
            "team2_img":  teams[1].get("image", "") if len(teams) > 1 else "",
            "winner":     winner,
        })
    return result


def get_match_games(match_id: str) -> list[dict]:
    """Retourne les games d'un match (pour les matchs BO3/BO5)."""
    data = _esports_get("getEventDetails", {"id": match_id})
    games = data.get("data", {}).get("event", {}).get("match", {}).get("games", [])
    return [{"id": g["id"], "number": g["number"], "state": g.get("state", "")} for g in games]


def _parse_timestamp(ts: str) -> datetime:
    """Parse RFC460 timestamp to UTC datetime."""
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _frame_to_features_min(frame: dict, game_minute: int) -> dict:
    """Version simplifiée : prend directement le game_minute."""
    return _frame_to_features(frame, None, None, game_minute_override=game_minute)


def _frame_to_features(frame: dict, prev_frame: dict | None, game_start: datetime | None, game_minute_override: int | None = None) -> dict:
    """Convertit un frame live stats en vecteur de features."""
    if game_minute_override is not None:
        game_time_minutes = game_minute_override
    else:
        ts = _parse_timestamp(frame["rfc460Timestamp"])
        elapsed_sec = (ts - game_start).total_seconds()
        game_time_minutes = max(0, int(elapsed_sec / 60))

    blue = frame.get("blueTeam", {})
    red  = frame.get("redTeam", {})

    blue_dragons = [d.lower() for d in blue.get("dragons", [])]
    red_dragons  = [d.lower() for d in red.get("dragons", [])]

    blue_kills = blue.get("totalKills", 0)
    red_kills  = red.get("totalKills", 0)

    # First blood: première frame où des kills existent
    first_blood = 0
    if blue_kills > 0 and red_kills == 0:
        first_blood = 1
    elif red_kills > 0 and blue_kills == 0:
        first_blood = -1
    elif blue_kills > 0 and red_kills > 0:
        first_blood = 1 if blue_kills >= red_kills else -1  # approximatif

    # First tower
    blue_towers = blue.get("towers", 0)
    red_towers  = red.get("towers", 0)
    first_tower = 0
    if blue_towers > 0 and red_towers == 0:
        first_tower = 1
    elif red_towers > 0 and blue_towers == 0:
        first_tower = -1
    elif blue_towers > 0 and red_towers > 0:
        first_tower = 1 if blue_towers >= red_towers else -1  # approximatif

    # Dragon soul (4 dragons sans elder = soul possible)
    dragon_soul = 0
    if len(blue_dragons) >= 4 and "elder" not in blue_dragons[-3:]:
        dragon_soul = 1
    elif len(red_dragons) >= 4 and "elder" not in red_dragons[-3:]:
        dragon_soul = -1

    # Elder active (présent dans la liste)
    elder_active = 0
    if "elder" in blue_dragons:
        elder_active = 1
    elif "elder" in red_dragons:
        elder_active = -1

    # CS et level par joueur
    blue_cs    = sum(p.get("creepScore", 0) for p in blue.get("participants", []))
    red_cs     = sum(p.get("creepScore", 0) for p in red.get("participants", []))
    blue_level = sum(p.get("level", 0)      for p in blue.get("participants", []))
    red_level  = sum(p.get("level", 0)      for p in red.get("participants", []))

    return {
        "game_time_minutes":  game_time_minutes,
        "gold_diff":          blue.get("totalGold", 0) - red.get("totalGold", 0),
        "kills_diff":         blue_kills - red_kills,
        "cs_diff":            blue_cs - red_cs,
        "level_diff":         blue_level - red_level,
        "towers_diff":        blue_towers - red_towers,
        "dragons_diff":       len(blue_dragons) - len(red_dragons),
        "barons_diff":        blue.get("barons", 0) - red.get("barons", 0),
        "inhibitors_diff":    blue.get("inhibitors", 0) - red.get("inhibitors", 0),
        "first_blood":        first_blood,
        "first_tower":        first_tower,
        "dragon_soul":        dragon_soul,
        "elder_active":       elder_active,
        "infernal_diff":      sum(1 for d in blue_dragons if d in DRAGON_FIRE)
                            - sum(1 for d in red_dragons  if d in DRAGON_FIRE),
        "ocean_diff":         sum(1 for d in blue_dragons if d in DRAGON_OCEAN)
                            - sum(1 for d in red_dragons  if d in DRAGON_OCEAN),
        # Features non disponibles → 0
        "deaths_diff": 0, "heralds_diff": 0, "kills_last_3min": 0,
        "wards_diff": 0, "damage_diff": 0, "xp_diff": 0,
        "plates_diff": 0, "current_gold_diff": 0, "cc_diff": 0,
        "void_grubs_diff": 0, "powerspike_diff": 0,
    }


def _floor_to_minute(ts: str) -> datetime:
    """Retourne le datetime à la minute entière (sec=0, ms=0)."""
    dt = _parse_timestamp(ts)
    return dt.replace(second=0, microsecond=0)


def fetch_game_curve(esports_game_id: str, predict_fn) -> dict | None:
    """
    Récupère les données d'une game de tournoi et calcule la courbe win%.
    Stratégie : requêtes à chaque minute entière (HH:MM:00.000Z).
    L'API live stats retourne des données pour les timestamps entiers.
    """
    # 1. Fetch premier batch → T0 (timestamp de début)
    first_batch = _live_get(esports_game_id)
    if not first_batch or not first_batch.get("frames"):
        return None

    meta = first_batch.get("gameMetadata", {})
    # Arrondir T0 à la minute entière
    t0_raw = first_batch["frames"][0]["rfc460Timestamp"]
    t_current = _floor_to_minute(t0_raw)

    # 2. Requêtes minute par minute jusqu'à fin de game (max 50 min)
    raw_snapshots: list[tuple[int, dict]] = []  # (game_minute, last_frame)
    game_minute = 0
    consecutive_empty = 0

    for step in range(55):  # max 55 minutes
        ts_str = t_current.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        batch = _live_get(esports_game_id, starting_time=ts_str)
        frames = batch.get("frames", []) if batch else []

        if not frames:
            consecutive_empty += 1
            if consecutive_empty >= 3:
                break
            t_current += timedelta(minutes=1)
            continue

        consecutive_empty = 0
        last_frame = frames[-1]
        blue_gold = last_frame.get("blueTeam", {}).get("totalGold", 0)

        # Détecter le début du jeu (première minute avec gold > 1000)
        if blue_gold > 1000 or raw_snapshots:
            raw_snapshots.append((game_minute, last_frame))
            game_minute += 1

        if last_frame.get("gameState") in ("finished", "game_over"):
            break

        t_current += timedelta(minutes=1)
        time.sleep(0.06)

    if not raw_snapshots:
        return None

    # 3. Gagnant : équipe avec le plus de towers/barons dans la dernière frame (heuristique)
    last = raw_snapshots[-1][1]
    blue_last = last.get("blueTeam", {})
    red_last  = last.get("redTeam", {})
    # Heuristique gagnant : tours + inhibiteurs + barons
    def score(team: dict) -> int:
        return team.get("towers", 0) * 3 + team.get("inhibitors", 0) * 5 + team.get("barons", 0) * 2
    blue_won = score(blue_last) >= score(red_last)

    # 4. Construire la courbe minute par minute (lissée)
    from src.models.predict import smooth_probabilities
    snaps = [(gm, _frame_to_features_min(fr, gm)) for gm, fr in raw_snapshots if gm >= 3]
    probs = smooth_probabilities([predict_fn(feat) for _, feat in snaps])
    curve = []
    for (game_min, feat), p_blue in zip(snaps, probs):
        curve.append({
            "minute":        game_min,
            "blue_win_prob": round(p_blue * 100, 1),
            "gold_diff":     feat["gold_diff"],
            "kills_diff":    feat["kills_diff"],
        })

    duration_min = raw_snapshots[-1][0] if raw_snapshots else 0

    # 5. Construire blame simplifié depuis dernière frame
    blame = []
    for team_key, team_data in [("blue", blue_last), ("red", red_last)]:
        for p in team_data.get("participants", []):
            pid = p.get("participantId", 0)
            # Retrouver le nom depuis metadata
            team_meta = meta.get("blueTeamMetadata" if team_key == "blue" else "redTeamMetadata", {})
            participants_meta = team_meta.get("participantMetadata", [])
            pm = next((x for x in participants_meta if x.get("participantId") == pid), {})
            name    = pm.get("summonerName", f"P{pid}")
            champ   = pm.get("championId", "?")
            kills   = p.get("kills", 0)
            deaths  = p.get("deaths", 0)
            assists = p.get("assists", 0)
            team_kills = team_data.get("totalKills", 1) or 1
            kp = round((kills + assists) / team_kills * 100)
            impact = kp * 0.5 - deaths * 3
            blame.append({
                "pid": pid,
                "name": name,
                "champion": champ,
                "team": team_key,
                "won": (team_key == "blue") == blue_won,
                "kills": kills, "deaths": deaths, "assists": assists,
                "kda_str": f"{kills}/{deaths}/{assists}",
                "kill_participation": kp,
                "wards_placed": 0, "wards_killed": 0,
                "cs": p.get("creepScore", 0),
                "gold": p.get("totalGold", 0),
                "impact_score": round(impact, 1),
            })

    blame.sort(key=lambda x: x["impact_score"], reverse=True)

    return {
        "esports_game_id": esports_game_id,
        "blue_won":     blue_won,
        "duration_min": duration_min,
        "curve":        curve,
        "blame":        blame,
        "note":         "Données lolesports live stats — features partielles (gold/kills/tours/dragons)",
    }
