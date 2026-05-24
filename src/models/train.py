"""
Entraînement LogReg (baseline) + XGBoost (final) avec calibration.

Usage :
    python src/models/train.py
    python src/models/train.py --input data/processed/features.parquet
"""

import argparse
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    RocCurveDisplay,
    accuracy_score,
    log_loss,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from src.features.build_features import FEATURE_COLS, TARGET_COL

MODELS_DIR = Path("models")
MODELS_DIR.mkdir(exist_ok=True)


def load_data(path: str) -> tuple[pd.DataFrame, pd.Series]:
    df = pd.read_parquet(path)
    X = df[FEATURE_COLS]
    y = df[TARGET_COL]
    return X, y


def evaluate(name: str, model, X_test: pd.DataFrame, y_test: pd.Series) -> dict:
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    acc = accuracy_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_proba)
    ll = log_loss(y_test, y_proba)

    print(f"\n{'='*40}")
    print(f"  {name}")
    print(f"  Accuracy : {acc:.3f}")
    print(f"  AUC-ROC  : {auc:.3f}")
    print(f"  Log-loss : {ll:.3f}")
    print(f"{'='*40}")

    return {"name": name, "accuracy": acc, "auc": auc, "log_loss": ll,
            "model": model, "y_proba": y_proba}


def plot_results(results: list[dict], X_test: pd.DataFrame, y_test: pd.Series, X: pd.DataFrame):
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    fig.suptitle("Évaluation des modèles — Prédiction LoL", fontsize=14)

    # ROC curves
    ax = axes[0]
    for r in results:
        RocCurveDisplay.from_predictions(y_test, r["y_proba"], name=r["name"], ax=ax)
    ax.set_title("Courbes ROC")

    # Calibration curves
    ax = axes[1]
    for r in results:
        frac_pos, mean_pred = calibration_curve(y_test, r["y_proba"], n_bins=10)
        ax.plot(mean_pred, frac_pos, marker="o", label=r["name"])
    ax.plot([0, 1], [0, 1], "k--", label="Parfait")
    ax.set_xlabel("Probabilité prédite")
    ax.set_ylabel("Fréquence réelle")
    ax.set_title("Courbes de calibration")
    ax.legend()

    # Feature importance (XGBoost)
    xgb_result = next((r for r in results if "XGBoost" in r["name"]), None)
    if xgb_result:
        ax = axes[2]
        base_model = xgb_result["model"]
        if hasattr(base_model, "base_estimator"):
            base_model = base_model.base_estimator
        importances = pd.Series(
            base_model.feature_importances_, index=FEATURE_COLS
        ).sort_values()
        importances.plot(kind="barh", ax=ax, color="steelblue")
        ax.set_title("Feature importances (XGBoost)")

    plt.tight_layout()
    plt.savefig("models/evaluation.png", dpi=150)
    print("\nGraphiques sauvegardés → models/evaluation.png")


def train(input_path: str):
    print(f"Chargement des données : {input_path}")
    X, y = load_data(input_path)
    print(f"  {len(X)} snapshots, {y.mean():.1%} victoires équipe bleue")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    joblib.dump(scaler, MODELS_DIR / "scaler.pkl")

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    results = []

    # --- Logistic Regression (baseline) ---
    print("\nEntraînement : Logistic Regression...")
    lr = LogisticRegression(max_iter=1000, random_state=42)
    lr.fit(X_train_scaled, y_train)
    cv_auc_lr = cross_val_score(lr, X_train_scaled, y_train, cv=cv, scoring="roc_auc").mean()
    print(f"  CV AUC-ROC : {cv_auc_lr:.3f}")
    results.append(evaluate("Logistic Regression", lr, X_test_scaled, y_test))
    joblib.dump(lr, MODELS_DIR / "logreg.pkl")

    # --- XGBoost + calibration ---
    print("\nEntraînement : XGBoost...")
    xgb = XGBClassifier(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        use_label_encoder=False,
        eval_metric="logloss",
        random_state=42,
    )
    xgb.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)
    cv_auc_xgb = cross_val_score(xgb, X_train, y_train, cv=cv, scoring="roc_auc").mean()
    print(f"  CV AUC-ROC : {cv_auc_xgb:.3f}")

    # Calibration isotonique pour des probabilités fiables
    xgb_cal = CalibratedClassifierCV(xgb, method="isotonic", cv=5)
    xgb_cal.fit(X_train, y_train)
    results.append(evaluate("XGBoost (calibré)", xgb_cal, X_test, y_test))
    joblib.dump(xgb_cal, MODELS_DIR / "xgboost_final.pkl")

    plot_results(results, X_test, y_test, X)
    print("\nModèles sauvegardés dans models/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/processed/features.parquet")
    args = parser.parse_args()
    train(args.input)
