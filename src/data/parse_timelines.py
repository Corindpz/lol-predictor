"""
Transforme les timelines brutes Riot API en DataFrame de features.

Pour chaque match × timestamp, on calcule les différentiels bleu - rouge.
Participants 1-5 → équipe bleue (100), 6-10 → équipe rouge (200).
"""

import json
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from src.features.build_features import (
    BARON_BUFF_SEC, ELDER_BUFF_SEC, SLOPE_WINDOW, SNAPSHOT_MINUTES, TARGET_COL, is_dead,
)

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

BLUE_IDS = {1, 2, 3, 4, 5}
RED_IDS = {6, 7, 8, 9, 10}


def _team_gold_at(frames: list[dict], idx: int) -> tuple[int, int]:
    """Or total (bleu, rouge) à la frame idx. (0, 0) si hors limites."""
    if idx < 0 or idx >= len(frames):
        return 0, 0
    blue = red = 0
    for pid_str, stats in frames[idx].get("participantFrames", {}).items():
        gold = stats.get("totalGold", 0)
        if int(pid_str) in BLUE_IDS:
            blue += gold
        else:
            red += gold
    return blue, red


def _blue_wins(info: dict) -> bool | None:
    for team in info.get("info", {}).get("teams", []):
        if team["teamId"] == 100:
            return team["win"]
    return None


def _match_meta(info: dict) -> dict:
    block = info.get("info", {})
    return {
        "game_creation": block.get("gameCreation", 0),
        "game_duration": block.get("gameDuration", 0),
        "game_version": block.get("gameVersion", ""),
        "queue_id": block.get("queueId", 0),
    }


def _extract_snapshot(frames: list[dict], target_min: int) -> dict | None:
    """État du jeu à target_min minutes à partir des frames de la timeline."""
    if target_min >= len(frames):
        return None

    frame = frames[target_min]
    pf = frame.get("participantFrames", {})
    if not pf:
        return None

    # Référence temporelle alignée sur fetch_player (frame_idx * 60) pour une
    # parité train/serve exacte sur les buffs et le calcul des joueurs vivants.
    target_sec = target_min * 60

    blue = {"cs": 0, "gold": 0, "level": 0, "damage": 0, "current_gold": 0, "kills": 0}
    red  = {"cs": 0, "gold": 0, "level": 0, "damage": 0, "current_gold": 0, "kills": 0}
    level_by_pid: dict[int, int] = {}

    for pid_str, stats in pf.items():
        pid = int(pid_str)
        bucket = blue if pid in BLUE_IDS else red
        bucket["cs"] += stats.get("minionsKilled", 0) + stats.get("jungleMinionsKilled", 0)
        bucket["gold"] += stats.get("totalGold", 0)
        bucket["level"] += stats.get("level", 0)
        bucket["current_gold"] += stats.get("currentGold", 0)
        bucket["damage"] += stats.get("damageStats", {}).get("totalDamageDoneToChampions", 0)
        level_by_pid[pid] = stats.get("level", 1)

    towers_blue = towers_red = 0
    inhibitors_blue = inhibitors_red = 0
    dragons_blue = dragons_red = 0
    heralds_blue = heralds_red = 0
    barons_blue = barons_red = 0
    plates_blue = plates_red = 0
    kills_blue_recent = kills_red_recent = 0
    first_blood = 0            # +1 = blue, -1 = red
    first_tower = 0            # +1 blue first, -1 red first
    first_tower_done = False
    void_grubs_blue = void_grubs_red = 0
    last_death_ts: dict[int, float] = {}
    last_baron_ts = last_elder_ts = -1e9
    last_baron_team = last_elder_team = 0

    for f_idx, f in enumerate(frames[:target_min + 1]):
        is_recent = f_idx >= max(0, target_min - 2)
        for event in f.get("events", []):
            etype = event.get("type")
            killer_team = event.get("killerTeamId", event.get("teamId", 0))
            ts = event.get("timestamp", 0) / 1000

            if etype == "CHAMPION_KILL":
                killer_id = event.get("killerId", 0)
                victim_id = event.get("victimId", 0)
                if killer_id in BLUE_IDS:
                    blue["kills"] += 1
                    if is_recent:
                        kills_blue_recent += 1
                    if first_blood == 0:
                        first_blood = 1
                elif killer_id in RED_IDS:
                    red["kills"] += 1
                    if is_recent:
                        kills_red_recent += 1
                    if first_blood == 0:
                        first_blood = -1
                if victim_id:
                    last_death_ts[victim_id] = ts

            elif etype == "BUILDING_KILL":
                # BUILDING_KILL: teamId = owner of the destroyed building (not the killer).
                btype = event.get("buildingType", "")
                if btype == "INHIBITOR_BUILDING":
                    if killer_team == 100:
                        inhibitors_red += 1
                    else:
                        inhibitors_blue += 1
                else:
                    if not first_tower_done:
                        first_tower = -1 if killer_team == 100 else 1
                        first_tower_done = True
                    if killer_team == 100:
                        towers_red += 1
                    else:
                        towers_blue += 1

            elif etype == "TURRET_PLATE_DESTROYED":
                if event.get("teamId", 0) == 100:
                    plates_red += 1
                else:
                    plates_blue += 1

            elif etype == "ELITE_MONSTER_KILL":
                monster = event.get("monsterType", "")
                subtype = event.get("monsterSubType", "")
                if monster == "DRAGON":
                    if subtype == "ELDER_DRAGON":
                        last_elder_ts = ts
                        last_elder_team = killer_team
                    elif killer_team == 100:
                        dragons_blue += 1
                    else:
                        dragons_red += 1
                elif monster == "BARON_NASHOR":
                    last_baron_ts = ts
                    last_baron_team = killer_team
                    if killer_team == 100:
                        barons_blue += 1
                    else:
                        barons_red += 1
                elif monster == "RIFTHERALD":
                    if killer_team == 100:
                        heralds_blue += 1
                    else:
                        heralds_red += 1
                elif monster == "HORDE":  # Void Grubs
                    if killer_team == 100:
                        void_grubs_blue += 1
                    else:
                        void_grubs_red += 1

    # Buffs épiques encore actifs à l'instant du snapshot.
    baron_active = 0
    if target_sec - last_baron_ts < BARON_BUFF_SEC:
        baron_active = 1 if last_baron_team == 100 else -1
    elder_active = 0
    if target_sec - last_elder_ts < ELDER_BUFF_SEC:
        elder_active = 1 if last_elder_team == 100 else -1

    # Soul au 4e dragon (dérivé du compte, l'event DRAGON_SOUL_GIVEN a teamId=0).
    dragon_soul = 1 if dragons_blue >= 4 else (-1 if dragons_red >= 4 else 0)

    # Joueurs vivants : un pid est mort si son dernier décès est plus récent
    # que son temps de réapparition estimé (niveau + temps de jeu).
    blue_alive = sum(
        1 for pid in BLUE_IDS
        if not is_dead(target_sec, last_death_ts.get(pid), level_by_pid.get(pid, 1), target_min)
    )
    red_alive = sum(
        1 for pid in RED_IDS
        if not is_dead(target_sec, last_death_ts.get(pid), level_by_pid.get(pid, 1), target_min)
    )

    # Momentum : pente du gold_diff sur la fenêtre glissante.
    gold_diff_now = blue["gold"] - red["gold"]
    prev_idx = max(0, target_min - SLOPE_WINDOW)
    gb, gr = _team_gold_at(frames, prev_idx)
    gold_slope = (gold_diff_now - (gb - gr)) / max(1, target_min - prev_idx)

    return {
        "gold_diff": gold_diff_now,
        "gold_slope": gold_slope,
        "current_gold_diff": blue["current_gold"] - red["current_gold"],
        "level_diff": blue["level"] - red["level"],
        "cs_diff": blue["cs"] - red["cs"],
        "kills_diff": blue["kills"] - red["kills"],
        "kills_last_3min": kills_blue_recent - kills_red_recent,
        "damage_diff": blue["damage"] - red["damage"],
        "players_alive_diff": blue_alive - red_alive,
        "first_blood": first_blood,
        "towers_diff": towers_blue - towers_red,
        "plates_diff": plates_blue - plates_red,
        "inhibitors_diff": inhibitors_blue - inhibitors_red,
        "first_tower": first_tower,
        "dragons_diff": dragons_blue - dragons_red,
        "dragon_soul": dragon_soul,
        "heralds_diff": heralds_blue - heralds_red,
        "barons_diff": barons_blue - barons_red,
        "baron_active": baron_active,
        "elder_active": elder_active,
        "void_grubs_diff": void_grubs_blue - void_grubs_red,
        "game_time_minutes": target_min,
    }


def parse_all(output_file: str = "data/processed/features.parquet") -> pd.DataFrame:
    timeline_files = list(RAW_DIR.glob("*_timeline.json"))
    print(f"{len(timeline_files)} timelines trouvées")

    rows = []
    for tl_path in tqdm(timeline_files):
        match_id = tl_path.stem.replace("_timeline", "")
        info_path = RAW_DIR / f"{match_id}_info.json"

        if not info_path.exists():
            continue

        try:
            timeline = json.loads(tl_path.read_text())
            info = json.loads(info_path.read_text())
        except Exception:
            continue

        winner = _blue_wins(info)
        if winner is None:
            continue

        meta = _match_meta(info)
        # Remakes / parties avortees : moins de 15 min => pas exploitable.
        if 0 < meta["game_duration"] < 15 * 60:
            continue

        frames = timeline.get("info", {}).get("frames", [])

        for snap_min in SNAPSHOT_MINUTES:
            snap = _extract_snapshot(frames, snap_min)
            if snap is None:
                continue
            snap[TARGET_COL] = int(winner)
            snap["match_id"] = match_id
            snap["game_creation"] = meta["game_creation"]
            snap["game_version"] = meta["game_version"]
            rows.append(snap)

    df = pd.DataFrame(rows)
    df.to_parquet(output_file, index=False)
    print(f"\n{len(df)} snapshots sauvegardés → {output_file}")
    return df


if __name__ == "__main__":
    parse_all()
