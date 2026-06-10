"""
JPTrades - Adaptive Model Retraining
Automatically retrains the model using latest market data.
ONLY deploys a new model if it outperforms the current one on validation data.
Never replaces a working model with a worse one.

Run daily after market close (3:30 PM+) or on a schedule.
Can also be triggered from the app.
"""

import numpy as np
import pandas as pd
import joblib
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path

from sklearn.ensemble import ExtraTreesClassifier
from sklearn.metrics import accuracy_score, f1_score, brier_score_loss
from sklearn.calibration import CalibratedClassifierCV

from market_data import MarketData
from config import MODEL_FILE, RANDOM_STATE

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
METADATA_FILE = BASE_DIR / "models" / "model_metadata.json"
BACKUP_DIR = BASE_DIR / "models" / "backups"
BACKUP_DIR.mkdir(exist_ok=True)

# Same features as train_model.py
FEATURES = [
    "RETURN_6", "EMA_DIFF", "MACD_SIGNAL", "VIX_RETURN_3", "MINUTE",
    "EMA50", "BB_UPPER", "BANK_RETURN_1", "EMA20", "RETURN_3", "MACD",
]

TARGET_HORIZON = 3
TARGET_THRESHOLD = 0.003


def load_current_metadata():
    """Load metadata of the currently deployed model."""
    if METADATA_FILE.exists():
        with open(METADATA_FILE) as f:
            return json.load(f)
    return None


def prepare_data():
    """Download fresh data and prepare features + target."""
    md = MarketData()
    data = md.get_processed_data()

    future_return = (data["Close"].shift(-TARGET_HORIZON) - data["Close"]) / data["Close"]
    data["TARGET"] = None
    data.loc[future_return > TARGET_THRESHOLD, "TARGET"] = 1
    data.loc[future_return < -TARGET_THRESHOLD, "TARGET"] = 0
    data = data.dropna(subset=["TARGET"])
    data["TARGET"] = data["TARGET"].astype(int)

    return data


def walk_forward_evaluate(X, y, n_folds=3):
    """
    Walk-forward validation to get realistic OOS performance.
    Returns average accuracy and F1 across folds.
    """
    n_total = len(X)
    fold_size = n_total // (n_folds + 2)  # +2 for minimum training size
    min_train = fold_size * 2

    accuracies = []
    f1_scores = []

    for fold_start in range(min_train, n_total - fold_size, fold_size):
        fold_end = min(fold_start + fold_size, n_total)

        X_tr = X.iloc[:fold_start]
        y_tr = y.iloc[:fold_start]
        X_te = X.iloc[fold_start:fold_end]
        y_te = y.iloc[fold_start:fold_end]

        if len(X_te) < 10 or len(X_tr) < 50:
            continue

        model = ExtraTreesClassifier(
            n_estimators=500, max_depth=8, min_samples_leaf=10,
            random_state=RANDOM_STATE, n_jobs=-1
        )
        model.fit(X_tr, y_tr)

        preds = model.predict(X_te)
        acc = accuracy_score(y_te, preds)
        f1 = f1_score(y_te, preds, zero_division=0)

        accuracies.append(acc)
        f1_scores.append(f1)

    if not accuracies:
        return 0.0, 0.0

    return float(np.mean(accuracies)), float(np.mean(f1_scores))


def train_candidate_model(X_train, y_train, X_val, y_val):
    """
    Train a new candidate model with calibration.
    Returns (calibrated_model, validation_accuracy, validation_f1, brier_score).
    """
    base_model = ExtraTreesClassifier(
        n_estimators=500, max_depth=8, min_samples_leaf=10,
        random_state=RANDOM_STATE, n_jobs=-1
    )
    base_model.fit(X_train, y_train)

    # Calibrate
    calibrated = CalibratedClassifierCV(base_model, method="isotonic", cv=5)
    calibrated.fit(X_train, y_train)

    # Evaluate on validation set
    val_preds = calibrated.predict(X_val)
    val_probs = calibrated.predict_proba(X_val)[:, 1]

    acc = accuracy_score(y_val, val_preds)
    f1 = f1_score(y_val, val_preds, zero_division=0)
    brier = brier_score_loss(y_val, val_probs)

    return calibrated, acc, f1, brier


def retrain():
    """
    Full retraining pipeline:
    1. Fetch latest data
    2. Train new candidate model
    3. Compare against current model
    4. Deploy ONLY if candidate is better

    Returns dict with results.
    """
    logger.info("=" * 50)
    logger.info("  ADAPTIVE RETRAINING STARTED")
    logger.info("=" * 50)

    # 1. Prepare fresh data
    logger.info("Loading fresh market data...")
    data = prepare_data()
    logger.info(f"Data: {len(data)} samples")

    if len(data) < 100:
        logger.warning("Insufficient data for retraining (need 100+)")
        return {"status": "skipped", "reason": "insufficient_data", "samples": len(data)}

    X = data[FEATURES]
    y = data["TARGET"]

    # 2. Walk-forward validation on new data
    logger.info("Running walk-forward validation...")
    wf_acc, wf_f1 = walk_forward_evaluate(X, y)
    logger.info(f"Walk-forward: Acc={wf_acc*100:.1f}%, F1={wf_f1:.3f}")

    # 3. Train candidate model (80/20 split for final evaluation)
    split = int(len(X) * 0.80)
    X_train, X_val = X.iloc[:split], X.iloc[split:]
    y_train, y_val = y.iloc[:split], y.iloc[split:]

    logger.info(f"Training candidate model (train={len(X_train)}, val={len(X_val)})...")
    candidate_model, val_acc, val_f1, val_brier = train_candidate_model(X_train, y_train, X_val, y_val)

    logger.info(f"Candidate: Acc={val_acc*100:.1f}%, F1={val_f1:.3f}, Brier={val_brier:.4f}")

    # 4. Compare with current model
    current_meta = load_current_metadata()
    current_acc = current_meta.get("oos_accuracy", 0) if current_meta else 0
    current_f1 = current_meta.get("oos_f1", 0) if current_meta else 0

    # Also test current model on the same validation set
    current_model_acc = 0
    if MODEL_FILE.exists():
        try:
            current_model = joblib.load(MODEL_FILE)
            current_preds = current_model.predict(X_val)
            current_model_acc = accuracy_score(y_val, current_preds)
            logger.info(f"Current model on same val set: {current_model_acc*100:.1f}%")
        except Exception as e:
            logger.warning(f"Could not evaluate current model: {e}")
            current_model_acc = 0

    # 5. Decision: deploy only if better
    # Candidate must beat current by at least 1% to avoid noise
    improvement = val_acc - current_model_acc
    should_deploy = improvement > 0.01 or current_model_acc == 0

    logger.info(f"\n  COMPARISON:")
    logger.info(f"    Current model val accuracy: {current_model_acc*100:.1f}%")
    logger.info(f"    Candidate val accuracy:     {val_acc*100:.1f}%")
    logger.info(f"    Improvement:                {improvement*100:+.1f}%")
    logger.info(f"    Decision:                   {'DEPLOY' if should_deploy else 'KEEP CURRENT'}")

    result = {
        "status": "deployed" if should_deploy else "kept_current",
        "candidate_accuracy": round(val_acc * 100, 2),
        "candidate_f1": round(val_f1, 3),
        "candidate_brier": round(val_brier, 4),
        "current_accuracy": round(current_model_acc * 100, 2),
        "improvement": round(improvement * 100, 2),
        "walk_forward_accuracy": round(wf_acc * 100, 2),
        "walk_forward_f1": round(wf_f1, 3),
        "data_samples": len(data),
        "timestamp": datetime.now().isoformat(),
    }

    if should_deploy:
        # Backup current model
        if MODEL_FILE.exists():
            backup_name = f"model_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
            shutil.copy2(MODEL_FILE, BACKUP_DIR / backup_name)
            logger.info(f"Current model backed up: {backup_name}")

        # Deploy new model
        joblib.dump(candidate_model, MODEL_FILE)

        # Update metadata
        metadata = {
            "features": FEATURES,
            "target_horizon": TARGET_HORIZON,
            "target_threshold": TARGET_THRESHOLD,
            "model_type": "CalibratedClassifierCV(ExtraTreesClassifier)",
            "walk_forward_accuracy": wf_acc,
            "walk_forward_f1": wf_f1,
            "oos_accuracy": val_acc,
            "oos_f1": val_f1,
            "brier_score": val_brier,
            "n_features": len(FEATURES),
            "training_samples": len(X_train),
            "trained_at": datetime.now().isoformat(),
            "improvement_over_previous": round(improvement * 100, 2),
        }
        with open(METADATA_FILE, "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info("NEW MODEL DEPLOYED SUCCESSFULLY")
    else:
        logger.info("Current model retained (candidate not significantly better)")

    # Log retrain history
    history_file = BASE_DIR / "models" / "retrain_history.json"
    history = []
    if history_file.exists():
        with open(history_file) as f:
            history = json.load(f)
    history.append(result)
    # Keep last 30 entries
    history = history[-30:]
    with open(history_file, "w") as f:
        json.dump(history, f, indent=2)

    logger.info("=" * 50)
    return result


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )
    result = retrain()
    print(f"\nResult: {result['status']}")
    print(f"Candidate accuracy: {result['candidate_accuracy']}%")
    print(f"Current accuracy:   {result['current_accuracy']}%")
    print(f"Improvement:        {result['improvement']:+.2f}%")
