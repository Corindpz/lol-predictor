"""
Compute champion role profiles from raw match data.
Outputs: data/processed/champion_roles.json
{
  "Jinx": {
    "BOTTOM":  {"games": 450, "wins": 234, "winrate": 0.52},
    "TOP":     {"games": 2,   "wins": 1,   "winrate": 0.50},
    ...
    "_primary": "BOTTOM"
  },
  ...
}
"""
import json
from collections import defaultdict
from pathlib import Path

RAW_DIR = Path("data/raw")
OUT_FILE = Path("data/processed/champion_roles.json")

VALID_ROLES = {"TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"}


def main():
    # {champion: {role: [wins, total]}}
    data: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(lambda: [0, 0]))

    info_files = sorted(RAW_DIR.glob("*_info.json"))
    print(f"Processing {len(info_files)} matches...")

    for i, path in enumerate(info_files):
        if i % 1000 == 0:
            print(f"  {i}/{len(info_files)}")
        try:
            with open(path) as f:
                d = json.load(f)
            for p in d["info"]["participants"]:
                champ = p.get("championName")
                role  = p.get("teamPosition", "")
                won   = p.get("win", False)
                if champ and role in VALID_ROLES:
                    data[champ][role][1] += 1
                    if won:
                        data[champ][role][0] += 1
        except Exception:
            continue

    result = {}
    for champ, roles in data.items():
        entry: dict = {}
        for role, (wins, total) in roles.items():
            entry[role] = {
                "games": total,
                "wins": wins,
                "winrate": round(wins / total, 4) if total else 0.5,
            }
        # Primary role = most games
        primary = max(entry, key=lambda r: entry[r]["games"])
        entry["_primary"] = primary
        result[champ] = entry

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "w") as f:
        json.dump(result, f, indent=2)
    print(f"Saved {len(result)} champions to {OUT_FILE}")

    # Quick sanity check
    for champ in ["Jinx", "Thresh", "Graves", "Malzahar", "Jax"]:
        if champ in result:
            e = result[champ]
            print(f"  {champ}: primary={e['_primary']}, roles={[r for r in e if not r.startswith('_')]}")


if __name__ == "__main__":
    main()
