"""
Train XGBoost draft win predictor.
Input: one-hot champion presence (blue + red teams, 344 features)
Output: blue win probability
"""
import json
import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import roc_auc_score, accuracy_score
from xgboost import XGBClassifier

DATA_FILE  = Path("data/processed/draft_features.parquet")
CHAMPS_FILE = Path("data/processed/draft_champions.csv")
OUT_MODEL  = Path("models/draft_xgb.pkl")
OUT_STATS  = Path("models/draft_stats.json")


def main():
    df = pd.read_parquet(DATA_FILE)
    champ_list = pd.read_csv(CHAMPS_FILE, header=None)[0].tolist()

    X = df.drop("blue_wins", axis=1).values.astype(np.float32)
    y = df["blue_wins"].values

    print(f"Dataset: {X.shape[0]} matchs × {X.shape[1]} features")
    print(f"Blue winrate: {y.mean()*100:.1f}%")

    # XGBoost — arbre peu profond pour éviter l'overfitting sur données sparses
    xgb = XGBClassifier(
        n_estimators=300,
        max_depth=3,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.4,
        min_child_weight=5,
        reg_alpha=1.0,
        reg_lambda=2.0,
        eval_metric="logloss",
        random_state=42,
        n_jobs=-1,
    )

    # Cross-validation 5-fold
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_results = cross_validate(
        xgb, X, y, cv=cv,
        scoring=["roc_auc", "accuracy"],
        return_train_score=True,
    )

    auc_cv  = cv_results["test_roc_auc"].mean()
    acc_cv  = cv_results["test_accuracy"].mean()
    auc_tr  = cv_results["train_roc_auc"].mean()
    print(f"\nCV (5-fold):")
    print(f"  AUC   train={auc_tr:.4f}  test={auc_cv:.4f}")
    print(f"  Acc   test={acc_cv*100:.1f}%")

    # Fit final sur tout le dataset + calibration
    xgb.fit(X, y)
    calibrated = CalibratedClassifierCV(xgb, cv="prefit", method="sigmoid")
    calibrated.fit(X, y)

    # Top features (champions les plus prédictifs)
    importances = xgb.feature_importances_
    feat_names = list(df.drop("blue_wins", axis=1).columns)
    top_feats = sorted(zip(feat_names, importances), key=lambda x: -x[1])[:20]
    print("\nTop 10 features (champions les plus discriminants) :")
    for feat, imp in top_feats[:10]:
        team = "Bleue" if feat.startswith("blue_") else "Rouge"
        champ = feat.split("_", 1)[1]
        print(f"  {champ} ({team}): {imp:.4f}")

    # Save
    joblib.dump(calibrated, OUT_MODEL)
    stats = {
        "auc_cv": round(float(auc_cv), 4),
        "acc_cv": round(float(acc_cv), 4),
        "auc_train": round(float(auc_tr), 4),
        "n_samples": int(X.shape[0]),
        "n_features": int(X.shape[1]),
        "n_champions": len(champ_list),
        "top_features": [{"feature": f, "importance": round(float(i), 5)} for f, i in top_feats],
    }
    OUT_STATS.write_text(json.dumps(stats, indent=2))
    print(f"\nModèle sauvegardé: {OUT_MODEL}")
    print(f"Stats sauvegardées: {OUT_STATS}")
    return stats


if __name__ == "__main__":
    main()
