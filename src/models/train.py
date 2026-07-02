"""
Entraînement LogReg (baselines) + XGBoost (final) avec calibration.

Split temporel par game (pas de fuite entre snapshots d'une meme partie) et
CV groupee sur match_id. Metriques : accuracy, AUC, log-loss, Brier, ECE,
plus une ventilation par minute de jeu.

Usage :
    python src/models/train.py
    python src/models/train.py --tune
    python src/models/train.py --input data/processed/features.parquet
"""

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.frozen import FrozenEstimator
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    RocCurveDisplay,
    accuracy_score,
    brier_score_loss,
    log_loss,
    roc_auc_score,
)
from sklearn.model_selection import (
    GroupShuffleSplit, RandomizedSearchCV, StratifiedGroupKFold, cross_val_score
)
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier
from scipy.stats import randint, uniform

from src.features.build_features import FEATURE_COLS, TARGET_COL

MODELS_DIR = Path("models")
MODELS_DIR.mkdir(exist_ok=True)
RESULTS_DIR = Path("docs/results")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

TEST_FRACTION = 0.2
N_SPLITS = 5
RANDOM_STATE = 42


def load_data(path: str) -> pd.DataFrame:
    df = pd.read_parquet(path)
    if "match_id" not in df.columns:
        raise ValueError(
            "Colonne 'match_id' absente du parquet. Relance parse_timelines.py "
            "pour regenerer les features avec match_id (fix de la fuite de donnees)."
        )
    return df


def temporal_group_split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Test = les parties les plus recentes. Aucune game n'est a cheval sur
    train et test (split par match_id) -> pas de fuite de groupe, et reflet
    honnete de l'usage reel (predire des games futures)."""
    if "game_creation" in df.columns and df["game_creation"].gt(0).any():
        order = (
            df.groupby("match_id")["game_creation"].min().sort_values().index.tolist()
        )
        split_by = "date de creation (split temporel)"
    else:
        rng = np.random.default_rng(RANDOM_STATE)
        order = df["match_id"].unique().tolist()
        rng.shuffle(order)
        split_by = "aleatoire groupe (game_creation absent)"

    n_test = max(1, int(len(order) * TEST_FRACTION))
    test_ids = set(order[-n_test:])
    test_mask = df["match_id"].isin(test_ids)
    print(f"  Split {split_by} : {len(order) - n_test} games train / {n_test} games test")
    return df[~test_mask].copy(), df[test_mask].copy()


def expected_calibration_error(y_true, y_proba, n_bins: int = 10) -> float:
    """ECE : ecart moyen |confiance - precision| par bin de proba."""
    y_true = np.asarray(y_true)
    y_proba = np.asarray(y_proba)
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    idx = np.clip(np.digitize(y_proba, bins) - 1, 0, n_bins - 1)
    ece = 0.0
    n = len(y_true)
    for b in range(n_bins):
        mask = idx == b
        if not mask.any():
            continue
        conf = y_proba[mask].mean()
        acc = y_true[mask].mean()
        ece += (mask.sum() / n) * abs(acc - conf)
    return float(ece)


def score(name: str, y_test, y_proba) -> dict:
    y_pred = (y_proba >= 0.5).astype(int)
    acc = accuracy_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_proba)
    ll = log_loss(y_test, y_proba)
    brier = brier_score_loss(y_test, y_proba)
    ece = expected_calibration_error(y_test, y_proba)

    print(f"\n{'='*44}")
    print(f"  {name}")
    print(f"  Accuracy : {acc:.3f}")
    print(f"  AUC-ROC  : {auc:.3f}")
    print(f"  Log-loss : {ll:.3f}")
    print(f"  Brier    : {brier:.3f}")
    print(f"  ECE      : {ece:.3f}")
    print(f"{'='*44}")

    return {"name": name, "accuracy": acc, "auc": auc, "log_loss": ll,
            "brier": brier, "ece": ece, "y_proba": y_proba}


def metrics_by_minute(y_test, y_proba, minutes) -> list[dict]:
    """Ventilation des metriques par minute de jeu (sur le test set groupe)."""
    out = []
    minutes = np.asarray(minutes)
    y_test = np.asarray(y_test)
    y_proba = np.asarray(y_proba)
    for m in sorted(np.unique(minutes)):
        mask = minutes == m
        if mask.sum() < 30:
            continue
        yt, yp = y_test[mask], y_proba[mask]
        row = {
            "minute": int(m),
            "n": int(mask.sum()),
            "accuracy": float(accuracy_score(yt, (yp >= 0.5).astype(int))),
            "brier": float(brier_score_loss(yt, yp)),
        }
        if len(np.unique(yt)) == 2:
            row["auc"] = float(roc_auc_score(yt, yp))
        out.append(row)
    return out


def plot_results(results: list[dict], y_test, cal_model):
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    fig.suptitle("Evaluation des modeles — Prediction LoL (test temporel groupe)", fontsize=14)

    ax = axes[0]
    for r in results:
        RocCurveDisplay.from_predictions(y_test, r["y_proba"], name=r["name"], ax=ax)
    ax.set_title("Courbes ROC")

    ax = axes[1]
    for r in results:
        frac_pos, mean_pred = calibration_curve(y_test, r["y_proba"], n_bins=10)
        ax.plot(mean_pred, frac_pos, marker="o", label=r["name"])
    ax.plot([0, 1], [0, 1], "k--", label="Parfait")
    ax.set_xlabel("Probabilite predite")
    ax.set_ylabel("Frequence reelle")
    ax.set_title("Courbes de calibration")
    ax.legend()

    ax = axes[2]
    base_estimator = cal_model.calibrated_classifiers_[0].estimator
    # Deballe le FrozenEstimator si besoin pour recuperer l'XGBoost.
    base_estimator = getattr(base_estimator, "estimator", base_estimator)
    importances = pd.Series(
        base_estimator.feature_importances_, index=FEATURE_COLS
    ).sort_values()
    importances.plot(kind="barh", ax=ax, color="steelblue")
    ax.set_title("Feature importances (XGBoost)")

    plt.tight_layout()
    plt.savefig("models/evaluation.png", dpi=150)
    print("\nGraphiques sauvegardes -> models/evaluation.png")


BEST_PARAMS_PATH = MODELS_DIR / "best_params.json"

DEFAULT_PARAMS = {
    "n_estimators": 300, "max_depth": 5, "learning_rate": 0.05,
    "subsample": 0.8, "colsample_bytree": 0.8,
    "min_child_weight": 1, "gamma": 0, "reg_alpha": 0, "reg_lambda": 1,
}

PARAM_DIST = {
    "n_estimators": randint(200, 900),
    "max_depth": randint(3, 8),
    "learning_rate": uniform(0.01, 0.15),
    "subsample": uniform(0.6, 0.4),
    "colsample_bytree": uniform(0.5, 0.5),
    "min_child_weight": randint(1, 8),
    "gamma": uniform(0, 0.5),
    "reg_alpha": uniform(0, 1),
    "reg_lambda": uniform(0.5, 2),
}


def tune_xgboost(X_train, y_train, groups, n_iter: int = 40) -> dict:
    print(f"\nTuning XGBoost ({n_iter} iterations, CV groupee)...")
    cv = StratifiedGroupKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)
    xgb_base = XGBClassifier(eval_metric="logloss", random_state=RANDOM_STATE)
    search = RandomizedSearchCV(
        xgb_base, PARAM_DIST, n_iter=n_iter, cv=cv,
        scoring="roc_auc", n_jobs=-1, random_state=RANDOM_STATE, verbose=1,
    )
    search.fit(X_train, y_train, groups=groups)
    best = search.best_params_
    print(f"  Meilleurs hyperparams : {best}")
    print(f"  CV AUC-ROC (groupee) : {search.best_score_:.4f}")
    BEST_PARAMS_PATH.write_text(json.dumps(best, indent=2))
    print(f"  Sauvegarde -> {BEST_PARAMS_PATH}")
    return best


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return "unknown"


def train(input_path: str, do_tune: bool = False):
    print(f"Chargement des donnees : {input_path}")
    df = load_data(input_path)
    print(f"  {len(df)} snapshots, {df[TARGET_COL].mean():.1%} victoires equipe bleue")

    train_df, test_df = temporal_group_split(df)
    X_train, y_train = train_df[FEATURE_COLS], train_df[TARGET_COL]
    X_test, y_test = test_df[FEATURE_COLS], test_df[TARGET_COL]
    groups_train = train_df["match_id"]
    cv = StratifiedGroupKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)

    results = []

    # --- Baseline 1 : Logistic Regression sur gold_diff seul ---
    # Temoin minimal : cadre la valeur ajoutee reelle de toutes les autres features.
    print("\nEntrainement : baseline gold_diff seul...")
    gd_scaler = StandardScaler()
    Xg_train = gd_scaler.fit_transform(X_train[["gold_diff"]])
    Xg_test = gd_scaler.transform(X_test[["gold_diff"]])
    lr_gold = LogisticRegression(max_iter=1000, random_state=RANDOM_STATE)
    lr_gold.fit(Xg_train, y_train)
    results.append(score("Baseline gold_diff", y_test, lr_gold.predict_proba(Xg_test)[:, 1]))

    # --- Baseline 2 : Logistic Regression sur toutes les features ---
    print("\nEntrainement : Logistic Regression (toutes features)...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    joblib.dump(scaler, MODELS_DIR / "scaler.pkl")
    lr = LogisticRegression(max_iter=1000, random_state=RANDOM_STATE)
    lr.fit(X_train_scaled, y_train)
    cv_auc_lr = cross_val_score(
        lr, X_train_scaled, y_train, groups=groups_train, cv=cv, scoring="roc_auc"
    ).mean()
    print(f"  CV AUC-ROC (groupee) : {cv_auc_lr:.3f}")
    results.append(score("Logistic Regression", y_test, lr.predict_proba(X_test_scaled)[:, 1]))
    joblib.dump(lr, MODELS_DIR / "logreg.pkl")

    # --- Hyperparametres ---
    if do_tune:
        best_params = tune_xgboost(X_train, y_train, groups_train, n_iter=40)
    elif BEST_PARAMS_PATH.exists():
        best_params = json.loads(BEST_PARAMS_PATH.read_text())
        print(f"\nHyperparams charges depuis {BEST_PARAMS_PATH}")
    else:
        best_params = DEFAULT_PARAMS
        print("\nHyperparams par defaut (lancez avec --tune pour optimiser)")

    # --- XGBoost + calibration ---
    print("\nEntrainement : XGBoost...")
    xgb = XGBClassifier(**best_params, eval_metric="logloss", random_state=RANDOM_STATE)
    cv_auc_xgb = cross_val_score(
        xgb, X_train, y_train, groups=groups_train, cv=cv, scoring="roc_auc"
    ).mean()
    print(f"  CV AUC-ROC (groupee) : {cv_auc_xgb:.3f}")

    # Calibration Platt sur un hold-out GROUPE (pas de fuite entre snapshots d'une
    # meme game). On evite le routing groups de CalibratedClassifierCV (non supporte
    # par StratifiedGroupKFold) : on isole 20% des games pour la calibration.
    gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=RANDOM_STATE)
    fit_idx, cal_idx = next(gss.split(X_train, y_train, groups=groups_train))
    # XGBoost régularisé est déjà quasi calibré (log-loss) ; l'isotonic préserve
    # cette qualité (ECE ~0.027) là où le sigmoid/Platt la dégradait (~0.048).
    xgb_fit = XGBClassifier(**best_params, eval_metric="logloss", random_state=RANDOM_STATE)
    xgb_fit.fit(X_train.iloc[fit_idx], y_train.iloc[fit_idx])
    xgb_cal = CalibratedClassifierCV(FrozenEstimator(xgb_fit), method="isotonic")
    xgb_cal.fit(X_train.iloc[cal_idx], y_train.iloc[cal_idx])
    xgb_proba = xgb_cal.predict_proba(X_test)[:, 1]
    results.append(score("XGBoost (calibre)", y_test, xgb_proba))
    joblib.dump(xgb_cal, MODELS_DIR / "xgboost_final.pkl")

    plot_results(results, y_test, xgb_cal)

    by_minute = metrics_by_minute(y_test, xgb_proba, test_df["game_time_minutes"])
    print("\nAUC / accuracy / Brier par minute (XGBoost, test groupe) :")
    for row in by_minute:
        print(f"  min {row['minute']:>2} | n={row['n']:>5} | "
              f"acc {row['accuracy']:.3f} | auc {row.get('auc', float('nan')):.3f} | "
              f"brier {row['brier']:.3f}")

    # --- Export metriques + meta versionnee du modele ---
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    metrics_export = {
        "run_id": run_id,
        "date": datetime.now().isoformat(),
        "git_sha": _git_sha(),
        "split": "temporel groupe par match_id",
        "dataset": {
            "n_samples": len(df),
            "n_features": len(FEATURE_COLS),
            "blue_win_rate": float(df[TARGET_COL].mean()),
            "n_games": int(df["match_id"].nunique()),
        },
        "cv_auc": {"logreg": float(cv_auc_lr), "xgboost": float(cv_auc_xgb)},
        "models": [{k: v for k, v in r.items() if k != "y_proba"} for r in results],
        "by_minute": by_minute,
    }
    metrics_path = RESULTS_DIR / f"run_{run_id}.json"
    metrics_path.write_text(json.dumps(metrics_export, indent=2))
    print(f"Metriques exportees -> {metrics_path}")

    # Meta chargee a l'inference pour verifier la coherence des features.
    meta = {
        "version": run_id,
        "date": datetime.now().isoformat(),
        "git_sha": _git_sha(),
        "feature_cols": FEATURE_COLS,
        "n_features": len(FEATURE_COLS),
        "target": TARGET_COL,
    }
    (MODELS_DIR / "model_meta.json").write_text(json.dumps(meta, indent=2))
    print("Meta modele -> models/model_meta.json")
    print("\nModeles sauvegardes dans models/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/processed/features.parquet")
    parser.add_argument("--tune", action="store_true", help="RandomizedSearchCV (CV groupee)")
    args = parser.parse_args()
    train(args.input, do_tune=args.tune)
