"""
Définition centralisée des features — partagée entre entraînement et inférence live.
Toute modification ici affecte les deux pipelines.
"""

FEATURE_COLS = [
    "kills_diff",
    "deaths_diff",
    "cs_diff",
    "gold_diff",
    "level_diff",
    "towers_diff",
    "dragons_diff",
    "heralds_diff",
    "barons_diff",
    "kills_last_3min",
    "game_time_minutes",
    # v2 features
    "wards_diff",
    "inhibitors_diff",
    "damage_diff",
    "first_blood",
    # v3 features
    "xp_diff",
    "plates_diff",
    "current_gold_diff",
    "dragon_soul",
    "cc_diff",
]

TARGET_COL = "blue_wins"

SNAPSHOT_MINUTES = [10, 15, 20, 25, 30]


def diff(blue_val: float, red_val: float) -> float:
    return blue_val - red_val
