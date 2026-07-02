"""
Définition centralisée des features — partagée entre entraînement et inférence.
Toute modification ici affecte les deux pipelines (parse_timelines + fetch_player).

v6 : jeu de features assaini et renforcé.
  - Ajouts fort signal : gold_slope (momentum), players_alive_diff (4v5 late),
    baron_active (buff actif != baron cumulé).
  - Retraits redondants/bruités : deaths_diff (~-kills_diff), xp_diff (~level_diff),
    les 6 diffs de drakes élémentaires (somme = dragons_diff), wards_diff, cc_diff,
    powerspike_diff.
"""

FEATURE_COLS = [
    # Économie
    "gold_diff",
    "gold_slope",          # momentum : pente du gold_diff sur les 5 dernières min
    "current_gold_diff",
    "level_diff",
    "cs_diff",
    # Combat
    "kills_diff",
    "kills_last_3min",     # diff des kills récents (momentum de teamfight)
    "damage_diff",
    "players_alive_diff",  # joueurs vivants bleu - rouge (avantage de teamfight)
    "first_blood",
    # Structures
    "towers_diff",
    "plates_diff",
    "inhibitors_diff",
    "first_tower",
    # Objectifs épiques
    "dragons_diff",
    "dragon_soul",
    "heralds_diff",
    "barons_diff",
    "baron_active",        # buff baron actif (+1 bleu / -1 rouge / 0)
    "elder_active",
    "void_grubs_diff",
    # Temps
    "game_time_minutes",
]

TARGET_COL = "blue_wins"

# Grille temporelle des snapshots : une capture par minute.
# Le modèle est servi minute par minute en jeu ; l'entraîner sur les mêmes
# instants supprime l'extrapolation (game_time_minutes est une feature).
# Un snapshot au-delà de la durée réelle de la game est ignoré au parsing.
SNAPSHOT_MINUTES = list(range(5, 41))

# Fenêtre (minutes) de la pente de gold (momentum).
SLOPE_WINDOW = 5

# Durée du buff Baron / Elder (secondes).
BARON_BUFF_SEC = 180
ELDER_BUFF_SEC = 150

# Temps de réapparition de base par niveau (Base Respawn Wait, secondes).
BASE_RESPAWN = {
    1: 10, 2: 10, 3: 12, 4: 12, 5: 14, 6: 16, 7: 20, 8: 25, 9: 28.5,
    10: 32.5, 11: 35, 12: 37.5, 13: 40, 14: 42.5, 15: 45, 16: 47.5,
    17: 50, 18: 52.5,
}


def death_timer(level: int, game_min: float) -> float:
    """Temps de mort estimé : BRW(niveau) majoré par le temps de jeu.
    Le facteur temps passe de +0% (avant 15 min) à +50% (a 45 min)."""
    brw = BASE_RESPAWN.get(max(1, min(18, int(level))), 10)
    time_factor = max(0.0, min((game_min - 15) / 30.0, 1.0)) * 0.5
    return brw * (1 + time_factor)


def is_dead(current_sec: float, last_death_sec: float | None,
            level: int, game_min: float) -> bool:
    """Un champion est considéré mort si son dernier décès est plus récent
    que son temps de réapparition estimé."""
    if last_death_sec is None:
        return False
    return (current_sec - last_death_sec) < death_timer(level, game_min)


def diff(blue_val: float, red_val: float) -> float:
    return blue_val - red_val
