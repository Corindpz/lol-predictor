"""
Build draft dataset from raw match info files.
Each row = one match, features = one-hot champion presence (blue + red teams).
Output: data/processed/draft_features.parquet
"""
import json
from pathlib import Path
import pandas as pd

RAW_DIR = Path("data/raw")
OUT_FILE = Path("data/processed/draft_features.parquet")
ROLES = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]


def main():
    # First pass: collect all unique champions
    print("Pass 1: collecting champions...")
    all_champs: set[str] = set()
    info_files = sorted(RAW_DIR.glob("*_info.json"))
    for path in info_files:
        try:
            d = json.loads(path.read_text())
            for p in d["info"]["participants"]:
                c = p.get("championName")
                if c:
                    all_champs.add(c)
        except Exception:
            continue

    champ_list = sorted(all_champs)
    champ_idx  = {c: i for i, c in enumerate(champ_list)}
    n = len(champ_list)
    print(f"  {n} unique champions")

    # Second pass: build feature matrix
    # Features: [blue_champ_0...blue_champ_N, red_champ_0...red_champ_N, blue_wins]
    print("Pass 2: building rows...")
    rows = []
    for path in info_files:
        try:
            d = json.loads(path.read_text())
            participants = d["info"]["participants"]

            blue = [p for p in participants if p.get("teamId") == 100]
            red  = [p for p in participants if p.get("teamId") == 200]
            if len(blue) != 5 or len(red) != 5:
                continue

            blue_won = blue[0].get("win", False)

            # One-hot per team
            blue_vec = [0] * n
            red_vec  = [0] * n
            for p in blue:
                c = p.get("championName")
                if c in champ_idx:
                    blue_vec[champ_idx[c]] = 1
            for p in red:
                c = p.get("championName")
                if c in champ_idx:
                    red_vec[champ_idx[c]] = 1

            rows.append(blue_vec + red_vec + [int(blue_won)])
        except Exception:
            continue

    print(f"  {len(rows)} valid matches")

    # Build DataFrame with meaningful column names
    blue_cols = [f"blue_{c}" for c in champ_list]
    red_cols  = [f"red_{c}"  for c in champ_list]
    df = pd.DataFrame(rows, columns=blue_cols + red_cols + ["blue_wins"])

    # Save champion list alongside
    pd.Series(champ_list).to_csv("data/processed/draft_champions.csv", index=False, header=False)
    df.to_parquet(OUT_FILE, index=False)
    print(f"Saved: {OUT_FILE}  shape={df.shape}")
    print(f"Blue winrate: {df['blue_wins'].mean()*100:.1f}%")
    return df


if __name__ == "__main__":
    main()
