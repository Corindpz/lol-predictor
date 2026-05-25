"""
Compute champion pair synergy scores from raw match data.
Outputs: data/processed/synergy_scores.json
"""
import json
import os
from collections import defaultdict
from itertools import combinations
from pathlib import Path

RAW_DIR = Path("data/raw")
OUT_FILE = Path("data/processed/synergy_scores.json")


def main():
    pair_wins = defaultdict(int)
    pair_games = defaultdict(int)

    info_files = sorted(RAW_DIR.glob("*_info.json"))
    print(f"Processing {len(info_files)} matches...")

    for i, path in enumerate(info_files):
        if i % 1000 == 0:
            print(f"  {i}/{len(info_files)}")
        try:
            with open(path) as f:
                data = json.load(f)
            participants = data["info"]["participants"]

            # Group by team
            teams: dict[int, list] = {100: [], 200: []}
            for p in participants:
                tid = p.get("teamId")
                champ = p.get("championName")
                won = p.get("win", False)
                if tid in teams and champ:
                    teams[tid].append((champ, won))

            for tid, players in teams.items():
                if len(players) != 5:
                    continue
                won = players[0][1]
                champs = [p[0] for p in players]
                for a, b in combinations(sorted(champs), 2):
                    key = f"{a}|{b}"
                    pair_games[key] += 1
                    if won:
                        pair_wins[key] += 1

        except Exception:
            continue

    # Build output: only pairs with >= 5 games
    result = {}
    for key, games in pair_games.items():
        if games >= 5:
            wr = pair_wins[key] / games
            result[key] = {"games": games, "winrate": round(wr, 4)}

    print(f"Pairs with >= 5 games: {len(result)}")
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "w") as f:
        json.dump(result, f)
    print(f"Saved to {OUT_FILE}")


if __name__ == "__main__":
    main()
