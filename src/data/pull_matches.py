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


def fetch_master_puuids(queue: str = "RANKED_SOLO_5x5") -> list[str]:
    """Retourne les PUUIDs des joueurs Master+ sur EUW.
    L'API retourne maintenant le puuid directement dans les entries — pas de requête intermédiaire.
    """
    url = f"https://{REGION}.api.riotgames.com/lol/league/v4/masterleagues/by-queue/{queue}"
    data = _get(url)
    if not data:
        raise RuntimeError("Impossible de récupérer les Master.")

    entries = data.get("entries", [])
    puuids = [e["puuid"] for e in entries if "puuid" in e]
    print(f"{len(entries)} joueurs Master EUW trouvés → {len(puuids)} PUUIDs récupérés instantanément")
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


def main(target_count: int):
    if not API_KEY:
        raise RuntimeError("RIOT_API_KEY manquante dans .env")

    puuids = fetch_master_puuids()
    collected = 0
    seen_ids = set()

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

            # On garde uniquement les parties ranked solo complètes (pas de remake)
            game_duration = info.get("info", {}).get("gameDuration", 0)
            if game_duration < 15 * 60:
                continue

            timeline = fetch_timeline(match_id)
            time.sleep(0.05)
            if timeline:
                collected += 1
                pbar.update(1)

    pbar.close()
    print(f"\n{collected} timelines sauvegardées dans {RAW_DIR}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=500)
    args = parser.parse_args()
    main(args.count)
