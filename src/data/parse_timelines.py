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

    blue, red = {}, {}
    for pid_str, stats in pf.items():
        pid = int(pid_str)
        bucket = blue if pid in BLUE_IDS else red
        bucket["kills"] = bucket.get("kills", 0) + stats.get("kills", 0)
        bucket["deaths"] = bucket.get("deaths", 0) + stats.get("deaths", 0)
        cs = stats.get("minionsKilled", 0) + stats.get("jungleMinionsKilled", 0)
        bucket["cs"] = bucket.get("cs", 0) + cs
        bucket["gold"] = bucket.get("gold", 0) + stats.get("totalGold", 0)
        bucket["level"] = bucket.get("level", 0) + stats.get("level", 0)

    if not blue or not red:
        return None

    # Objectifs cumulés jusqu'à target_min
    towers_blue = towers_red = 0
    dragons_blue = dragons_red = 0
    heralds_blue = heralds_red = 0
    barons_blue = barons_red = 0
    # Kills dans les 3 dernières minutes (momentum)
    kills_blue_recent = 0

    for f in frames[: target_min + 1]:
        recent = f is frames[max(0, target_min - 2) : target_min + 1][-1]  # noqa: simplification below
        for event in f.get("events", []):
            etype = event.get("type")
            killer_team = event.get("killerTeamId", event.get("teamId", 0))

            if etype == "BUILDING_KILL":
                if killer_team == 100:
                    towers_blue += 1
                else:
                    towers_red += 1

            elif etype == "ELITE_MONSTER_KILL":
                monster = event.get("monsterType", "")
                if monster == "DRAGON":
                    if killer_team == 100:
                        dragons_blue += 1
                    else:
                        dragons_red += 1
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

    # Kills des 3 dernières minutes pour le momentum
    for f in frames[max(0, target_min - 2) : target_min + 1]:
        for event in f.get("events", []):
            if event.get("type") == "CHAMPION_KILL":
                killer_id = event.get("killerId", 0)
                if killer_id in BLUE_IDS:
                    kills_blue_recent += 1

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
