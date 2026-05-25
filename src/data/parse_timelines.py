"""
Transforme les timelines brutes Riot API en DataFrame de features.

Pour chaque match × timestamp, on calcule les différentiels bleu - rouge.
Participants 1-5 → équipe bleue (100), 6-10 → équipe rouge (200).
"""

import json
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from src.features.build_features import FEATURE_COLS, SNAPSHOT_MINUTES, TARGET_COL

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

BLUE_IDS = {1, 2, 3, 4, 5}
RED_IDS = {6, 7, 8, 9, 10}

# Items qui créent des powerspikes significatifs (item IDs 2024-2025)
POWERSPIKE_ITEMS = {
    3157,  # Zhonya's Hourglass
    3089,  # Rabadon's Deathcap
    3078,  # Trinity Force
    3031,  # Infinity Edge
    6672,  # Kraken Slayer
    3071,  # Black Cleaver
    6655,  # Luden's Tempest
    4646,  # Stormsurge
}


def _blue_wins(info: dict) -> bool | None:
    for team in info.get("info", {}).get("teams", []):
        if team["teamId"] == 100:
            return team["win"]
    return None


def _extract_snapshot(frames: list[dict], target_min: int) -> dict | None:
    """État du jeu à target_min minutes à partir des frames de la timeline."""
    if target_min >= len(frames):
        return None

    frame = frames[target_min]
    pf = frame.get("participantFrames", {})

    blue = {"kills": 0, "deaths": 0, "cs": 0, "gold": 0, "level": 0, "damage": 0, "xp": 0, "current_gold": 0, "cc": 0}
    red  = {"kills": 0, "deaths": 0, "cs": 0, "gold": 0, "level": 0, "damage": 0, "xp": 0, "current_gold": 0, "cc": 0}

    for pid_str, stats in pf.items():
        pid = int(pid_str)
        bucket = blue if pid in BLUE_IDS else red
        cs = stats.get("minionsKilled", 0) + stats.get("jungleMinionsKilled", 0)
        bucket["cs"] += cs
        bucket["gold"] += stats.get("totalGold", 0)
        bucket["level"] += stats.get("level", 0)
        bucket["xp"] += stats.get("xp", 0)
        bucket["current_gold"] += stats.get("currentGold", 0)
        bucket["cc"] += stats.get("timeEnemySpentControlled", 0)
        bucket["damage"] += stats.get("damageStats", {}).get("totalDamageDoneToChampions", 0)

    if not pf:
        return None

    towers_blue = towers_red = 0
    inhibitors_blue = inhibitors_red = 0
    dragons_blue = dragons_red = 0
    heralds_blue = heralds_red = 0
    barons_blue = barons_red = 0
    wards_blue = wards_red = 0
    plates_blue = plates_red = 0
    kills_blue_recent = 0

    first_blood = 0        # +1 = blue, -1 = red
    dragon_soul = 0        # +1 = blue soul, -1 = red soul

    # v4 features
    void_grubs_blue = void_grubs_red = 0
    infernal_blue = infernal_red = 0
    ocean_blue = ocean_red = 0
    first_tower = 0            # +1 blue first, -1 red first
    first_tower_done = False
    elder_kill_frame = -999    # frame index of most recent elder kill
    elder_active_team = 0      # 100 or 200
    powerspike_blue = powerspike_red = 0
    # v5 features
    mountain_blue = mountain_red = 0
    cloud_blue = cloud_red = 0
    chemtech_blue = chemtech_red = 0
    hextech_blue = hextech_red = 0

    for f_idx, f in enumerate(frames[:target_min + 1]):
        is_recent = f_idx >= max(0, target_min - 2)
        for event in f.get("events", []):
            etype = event.get("type")
            killer_team = event.get("killerTeamId", event.get("teamId", 0))

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
                    if first_blood == 0:
                        first_blood = -1
                if victim_id in BLUE_IDS:
                    blue["deaths"] += 1
                elif victim_id in RED_IDS:
                    red["deaths"] += 1

            elif etype == "BUILDING_KILL":
                # BUILDING_KILL: teamId = owner of the destroyed building (not the killer).
                # teamId=100 → blue's building was killed by red → red team scores.
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

            elif etype == "ELITE_MONSTER_KILL":
                monster = event.get("monsterType", "")
                subtype = event.get("monsterSubType", "")

                if monster == "DRAGON":
                    if killer_team == 100:
                        dragons_blue += 1
                    else:
                        dragons_red += 1
                    if subtype == "FIRE_DRAGON":
                        if killer_team == 100:
                            infernal_blue += 1
                        else:
                            infernal_red += 1
                    elif subtype == "WATER_DRAGON":
                        if killer_team == 100:
                            ocean_blue += 1
                        else:
                            ocean_red += 1
                    elif subtype == "EARTH_DRAGON":
                        if killer_team == 100:
                            mountain_blue += 1
                        else:
                            mountain_red += 1
                    elif subtype == "AIR_DRAGON":
                        if killer_team == 100:
                            cloud_blue += 1
                        else:
                            cloud_red += 1
                    elif subtype == "CHEMTECH_DRAGON":
                        if killer_team == 100:
                            chemtech_blue += 1
                        else:
                            chemtech_red += 1
                    elif subtype == "HEXTECH_DRAGON":
                        if killer_team == 100:
                            hextech_blue += 1
                        else:
                            hextech_red += 1
                    elif subtype == "ELDER_DRAGON":
                        elder_kill_frame = f_idx
                        elder_active_team = killer_team

                elif monster == "BARON_NASHOR":
                    if killer_team == 100:
                        barons_blue += 1
                    else:
                        barons_red += 1

                elif monster == "RIFTHERALD":
                    if killer_team == 100:
                        heralds_blue += 1
                    else:
                        heralds_red += 1

                elif monster == "HORDE":  # Void Grubs (Season 14+)
                    if killer_team == 100:
                        void_grubs_blue += 1
                    else:
                        void_grubs_red += 1

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
                if soul_team == 100:
                    dragon_soul = 1
                else:
                    dragon_soul = -1

            elif etype == "ITEM_PURCHASED":
                pid = event.get("participantId", 0)
                item_id = event.get("itemId", 0)
                if item_id in POWERSPIKE_ITEMS:
                    if pid in BLUE_IDS:
                        powerspike_blue += 1
                    elif pid in RED_IDS:
                        powerspike_red += 1

    # Elder buff dure ~3 minutes (3 frames)
    if elder_kill_frame >= 0 and target_min - elder_kill_frame <= 3:
        elder_active = 1 if elder_active_team == 100 else -1
    else:
        elder_active = 0

    return {
        "kills_diff": blue["kills"] - red["kills"],
        "deaths_diff": blue["deaths"] - red["deaths"],
        "cs_diff": blue["cs"] - red["cs"],
        "gold_diff": blue["gold"] - red["gold"],
        "level_diff": blue["level"] - red["level"],
        "towers_diff": towers_blue - towers_red,
        "dragons_diff": dragons_blue - dragons_red,
        "heralds_diff": heralds_blue - heralds_red,
        "barons_diff": barons_blue - barons_red,
        "kills_last_3min": kills_blue_recent,
        "game_time_minutes": target_min,
        "wards_diff": wards_blue - wards_red,
        "inhibitors_diff": inhibitors_blue - inhibitors_red,
        "damage_diff": blue["damage"] - red["damage"],
        "first_blood": first_blood,
        "xp_diff": blue["xp"] - red["xp"],
        "plates_diff": plates_blue - plates_red,
        "current_gold_diff": blue["current_gold"] - red["current_gold"],
        "dragon_soul": dragon_soul,
        "cc_diff": blue["cc"] - red["cc"],
        # v4 features
        "void_grubs_diff": void_grubs_blue - void_grubs_red,
        "first_tower": first_tower,
        "infernal_diff": infernal_blue - infernal_red,
        "ocean_diff": ocean_blue - ocean_red,
        "elder_active": elder_active,
        "powerspike_diff": powerspike_blue - powerspike_red,
        # v5 features
        "mountain_diff": mountain_blue - mountain_red,
        "cloud_diff": cloud_blue - cloud_red,
        "chemtech_diff": chemtech_blue - chemtech_red,
        "hextech_diff": hextech_blue - hextech_red,
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

        frames = timeline.get("info", {}).get("frames", [])

        for snap_min in SNAPSHOT_MINUTES:
            snap = _extract_snapshot(frames, snap_min)
            if snap is None:
                continue
            snap[TARGET_COL] = int(winner)
            snap["match_id"] = match_id
            rows.append(snap)

    df = pd.DataFrame(rows)
    df.to_parquet(output_file, index=False)
    print(f"\n{len(df)} snapshots sauvegardés → {output_file}")
    return df


if __name__ == "__main__":
    parse_all()
