"""
Pull des matchs Master+ depuis la Riot API et sauvegarde des timelines brutes.

Usage :
    python src/data/pull_matches.py --count 500
    python src/data/pull_matches.py --count 3000  # tourne plusieurs heures

Rate limits dev key : 20 req/s, 100 req/2min → sleep intégré.
"""

import argparse
import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

API_KEY = os.getenv("RIOT_API_KEY")
REGION = os.getenv("REGION", "euw1")
MATCH_REGION = os.getenv("MATCH_REGION", "europe")

RAW_DIR = Path("data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {"X-Riot-Token": API_KEY}


def _get(url: str, params: dict = None, retries: int = 3) -> dict:
    for attempt in range(retries):
        resp = requests.get(url, headers=HEADERS, params=params, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", 10))
            time.sleep(retry_after)
        elif resp.status_code == 404:
            return None
        else:
            time.sleep(2 ** attempt)
    return None


TIER_ENDPOINTS = {
    "master":      f"https://{REGION}.api.riotgames.com/lol/league/v4/masterleagues/by-queue/RANKED_SOLO_5x5",
    "grandmaster": f"https://{REGION}.api.riotgames.com/lol/league/v4/grandmasterleagues/by-queue/RANKED_SOLO_5x5",
    "challenger":  f"https://{REGION}.api.riotgames.com/lol/league/v4/challengerleagues/by-queue/RANKED_SOLO_5x5",
}

def _tier_url(tier: str, div: str) -> str:
    return f"https://{REGION}.api.riotgames.com/lol/league/v4/entries/RANKED_SOLO_5x5/{tier.upper()}/{div}"

TIER_PAGES = {
    ("diamond",  "I"):   _tier_url("diamond",  "I"),
    ("diamond",  "II"):  _tier_url("diamond",  "II"),
    ("diamond",  "III"): _tier_url("diamond",  "III"),
    ("diamond",  "IV"):  _tier_url("diamond",  "IV"),
    ("platinum", "I"):   _tier_url("platinum", "I"),
    ("platinum", "II"):  _tier_url("platinum", "II"),
    ("platinum", "III"): _tier_url("platinum", "III"),
    ("platinum", "IV"):  _tier_url("platinum", "IV"),
    ("gold",     "I"):   _tier_url("gold",     "I"),
    ("gold",     "II"):  _tier_url("gold",     "II"),
    ("gold",     "III"): _tier_url("gold",     "III"),
    ("gold",     "IV"):  _tier_url("gold",     "IV"),
    ("silver",   "I"):   _tier_url("silver",   "I"),
    ("silver",   "II"):  _tier_url("silver",   "II"),
}


def fetch_puuids_apex(tier: str = "master") -> list[str]:
    """Master / Grandmaster / Challenger — le puuid est direct dans les entries."""
    url = TIER_ENDPOINTS.get(tier)
    if not url:
        raise ValueError(f"Tier inconnu : {tier}")
    data = _get(url)
    if not data:
        raise RuntimeError(f"Impossible de récupérer les {tier}.")
    entries = data.get("entries", [])
    puuids = [e["puuid"] for e in entries if "puuid" in e]
    print(f"  {len(entries)} joueurs {tier.capitalize()} EUW → {len(puuids)} PUUIDs")
    return puuids


def fetch_puuids_tier(tier: str, division: str, max_pages: int = 10) -> list[str]:
    """Diamond/Platinum/Gold — endpoint paginé, retourne summonerId → lookup PUUID."""
    url = TIER_PAGES.get((tier.lower(), division.upper()))
    if not url:
        raise ValueError(f"Tier/division inconnu : {tier} {division}")
    puuids = []
    for page in range(1, max_pages + 1):
        data = _get(url, params={"page": page})
        if not data:
            break
        for entry in data:
            puuid = entry.get("puuid")
            if puuid:
                puuids.append(puuid)
        if len(data) < 205:  # dernière page
            break
        time.sleep(0.5)
    print(f"  {len(puuids)} PUUIDs récupérés ({tier.capitalize()} {division})")
    return puuids


def fetch_match_ids(puuid: str, count: int = 20) -> list[str]:
    url = f"https://{MATCH_REGION}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
    params = {"queue": 420, "count": count}  # 420 = ranked solo
    return _get(url, params=params) or []


def fetch_timeline(match_id: str) -> dict | None:
    path = RAW_DIR / f"{match_id}_timeline.json"
    if path.exists():
        return json.loads(path.read_text())

    url = f"https://{MATCH_REGION}.api.riotgames.com/lol/match/v5/matches/{match_id}/timeline"
    data = _get(url)
    if data:
        path.write_text(json.dumps(data))
    return data


def fetch_match_info(match_id: str) -> dict | None:
    path = RAW_DIR / f"{match_id}_info.json"
    if path.exists():
        return json.loads(path.read_text())

    url = f"https://{MATCH_REGION}.api.riotgames.com/lol/match/v5/matches/{match_id}"
    data = _get(url)
    if data:
        path.write_text(json.dumps(data))
    return data


ALL_TIERS = [
    ("apex", "master"),
    ("apex", "grandmaster"),
    ("apex", "challenger"),
    ("tier", ("diamond",  "I")),
    ("tier", ("diamond",  "II")),
    ("tier", ("diamond",  "III")),
    ("tier", ("diamond",  "IV")),
    ("tier", ("platinum", "I")),
    ("tier", ("platinum", "II")),
    ("tier", ("platinum", "III")),
    ("tier", ("platinum", "IV")),
    ("tier", ("gold",     "I")),
    ("tier", ("gold",     "II")),
    ("tier", ("gold",     "III")),
    ("tier", ("gold",     "IV")),
    ("tier", ("silver",   "I")),
    ("tier", ("silver",   "II")),
]


def _collect_puuids_all() -> list[str]:
    """Collecte les PUUIDs de tous les tiers configurés."""
    all_puuids = []
    for kind, arg in ALL_TIERS:
        try:
            if kind == "apex":
                all_puuids.extend(fetch_puuids_apex(arg))
            else:
                all_puuids.extend(fetch_puuids_tier(*arg, max_pages=15))
        except Exception as e:
            print(f"  [skip] {arg} : {e}")
        time.sleep(0.3)
    return all_puuids


def main(target_count: int, tiers: str = "all"):
    if not API_KEY:
        raise RuntimeError("RIOT_API_KEY manquante dans .env")

    print(f"Collecte des PUUIDs ({tiers})...")
    if tiers == "master":
        puuids = fetch_puuids_apex("master")
    elif tiers == "all":
        puuids = _collect_puuids_all()
    else:
        puuids = fetch_puuids_apex(tiers) if tiers in ("grandmaster", "challenger") else []

    import random
    random.shuffle(puuids)
    print(f"Total PUUIDs : {len(puuids)}\n")

    collected = 0
    seen_ids = set()
    # Pré-charger les IDs déjà présents
    seen_ids = {f.stem.replace("_timeline", "") for f in RAW_DIR.glob("*_timeline.json")}
    print(f"  {len(seen_ids)} timelines déjà en cache (skip)")

    pbar = tqdm(total=target_count, desc="Timelines")
    for puuid in puuids:
        if collected >= target_count:
            break

        match_ids = fetch_match_ids(puuid, count=20)
        time.sleep(0.1)

        for match_id in match_ids:
            if collected >= target_count:
                break
            if match_id in seen_ids:
                continue
            seen_ids.add(match_id)

            info = fetch_match_info(match_id)
            time.sleep(0.05)
            if not info:
                continue

            game_duration = info.get("info", {}).get("gameDuration", 0)
            if game_duration < 15 * 60:
                continue

            timeline = fetch_timeline(match_id)
            time.sleep(0.05)
            if timeline:
                collected += 1
                pbar.update(1)

    pbar.close()
    print(f"\n{collected} nouvelles timelines → {RAW_DIR}/  (total cache : {len(seen_ids)})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=500)
    parser.add_argument("--tiers", default="all",
                        help="all | master | grandmaster | challenger")
    args = parser.parse_args()
    main(args.count, args.tiers)
