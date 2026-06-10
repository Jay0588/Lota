"""
JPTrades - Optimized Model Training
Based on quantitative audit findings:
  - 11 features (removed 13 noise features)
  - 0.3% move threshold (filters noise vs 0.2%)
  - Extra Trees primary model
  - Isotonic calibration for reliable confidence
  - Walk-forward validation
"""

import numpy as np
import pandas as pd
import joblib
import warnings
warnings.filterwarnings("ignore")

from sklearn.ensemble import ExtraTreesClassifier, GradientBoostingClassifier
from sklearn.metrics import accuracy_score, classification_report, f1_score, brier_score_loss
from sklearn.model_selection import train_test_split
from sklearn.calibration import CalibratedClassifierCV, calibration_curve

from market_data import MarketData
from config import MODEL_FILE, TEST_SIZE, RANDOM_STATE

# ══════════════════════════════════════════════════════════════════════════
# OPTIMIZED FEATURE SET (audit Phase 1 — permutation importance > 0)
# ══════════════════════════════════════════════════════════════════════════

FEATURES = [
    "RETURN_6",        # Most predictive: 6-bar momentum
    "EMA_DIFF",        # EMA20-EMA50 spread (trend strength)
    "MACD_SIGNAL",     # MACD signal line
    "VIX_RETURN_3",    # VIX 3-bar change (fear shift)
    "MINUTE",          # Intraday time (market microstructure)
    "EMA50",           # Medium-term trend level
    "BB_UPPER",        # Bollinger upper (resistance proxy)
    "BANK_RETURN_1",   # BankNifty 1-bar momentum (sector confirmation)
    "EMA20",           # Short-term trend level
    "RETURN_3",        # 3-bar momentum
    "MACD",            # MACD value
]

# Target: 0.3% move in 3 candles (15 min) — audit Phase 2 finding
TARGET_HORIZON = 3
TARGET_THRESHOLD = 0.003

print("=" * 60)
print("  JPTrades Model Training (Optimized)")
print("=" * 60)
print(f"\n  Features:  {len(FEATURES)} (reduced from 24)")
print(f"  Target:    {TARGET_HORIZON * 5}min, >{TARGET_THRESHOLD*100:.1f}% move")
print(f"  Model:     Extra Trees + Isotonic Calibration")

# ══════════════════════════════════════════════════════════════════════════
# LOAD DATA
# ══════════════════════════════════════════════════════════════════════════

print("\n  Loading market data...")
md = MarketData()
data = md.get_processed_data()
print(f"  Rows: {len(data)}")

# ══════════════════════════════════════════════════════════════════════════
# TARGET ENGINEERING
# ══════════════════════════════════════════════════════════════════════════

future_return = (data["Close"].shift(-TARGET_HORIZON) - data["Close"]) / data["Close"]

data["TARGET"] = None
data.loc[future_return > TARGET_THRESHOLD, "TARGET"] = 1   # UP >0.3%
data.loc[future_return < -TARGET_THRESHOLD, "TARGET"] = 0  # DOWN >0.3%

# Drop ambiguous rows (moves between -0.3% and +0.3%)
data = data.dropna(subset=["TARGET"])
data["TARGET"] = data["TARGET"].astype(int)

n_up = (data["TARGET"] == 1).sum()
n_down = (data["TARGET"] == 0).sum()
print(f"  Labeled samples: {len(data)} (UP: {n_up}, DOWN: {n_down}, balance: {n_up/len(data):.2f})")

X = data[FEATURES]
y = data["TARGET"]

# ══════════════════════════════════════════════════════════════════════════
# WALK-FORWARD VALIDATION (primary evaluation)
# ══════════════════════════════════════════════════════════════════════════

print("\n" + "-" * 60)
print("  Walk-Forward Validation")
print("-" * 60)

n_total = len(X)
fold_size = n_total // 5
min_train = fold_size * 2

wf_accuracies = []
wf_f1s = []
wf_win_rates_60 = []

for fold_start in range(min_train, n_total - fold_size, fold_size):
    fold_end = min(fold_start + fold_size, n_total)
    
    X_tr = X.iloc[:fold_start]
    y_tr = y.iloc[:fold_start]
    X_te = X.iloc[fold_start:fold_end]
    y_te = y.iloc[fold_start:fold_end]
    
    if len(X_te) < 10:
        continue
    
    wf_model = ExtraTreesClassifier(
        n_estimators=500, max_depth=8, min_samples_leaf=10,
        random_state=RANDOM_STATE, n_jobs=-1
    )
    wf_model.fit(X_tr, y_tr)
    
    wf_preds = wf_model.predict(X_te)
    wf_probs = wf_model.predict_proba(X_te)
    
    acc = accuracy_score(y_te, wf_preds)
    f1 = f1_score(y_te, wf_preds, zero_division=0)
    
    # Win rate at 60%+ confidence
    max_conf = np.max(wf_probs, axis=1)
    high_conf = max_conf >= 0.60
    if high_conf.sum() > 0:
        wr60 = accuracy_score(y_te[high_conf], wf_preds[high_conf])
    else:
        wr60 = 0
    
    wf_accuracies.append(acc)
    wf_f1s.append(f1)
    wf_win_rates_60.append(wr60)
    
    print(f"  Fold {len(wf_accuracies)}: Acc={acc*100:.1f}%  F1={f1:.3f}  WR@60%={wr60*100:.1f}%  (train={len(X_tr)}, test={len(X_te)})")

print(f"\n  Walk-Forward Average:")
print(f"    Accuracy:       {np.mean(wf_accuracies)*100:.2f}% ± {np.std(wf_accuracies)*100:.2f}%")
print(f"    F1 Score:       {np.mean(wf_f1s):.3f}")
print(f"    Win Rate @60%+: {np.mean(wf_win_rates_60)*100:.1f}%")

# ══════════════════════════════════════════════════════════════════════════
# FINAL MODEL TRAINING (on all data except last 20% for reporting)
# ══════════════════════════════════════════════════════════════════════════

print("\n" + "-" * 60)
print("  Training Final Model")
print("-" * 60)

split_idx = int(len(X) * 0.80)
X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

# Base model
base_model = ExtraTreesClassifier(
    n_estimators=500,
    max_depth=8,
    min_samples_leaf=10,
    random_state=RANDOM_STATE,
    n_jobs=-1
)
base_model.fit(X_train, y_train)

# Raw performance
raw_preds = base_model.predict(X_test)
raw_probs = base_model.predict_proba(X_test)[:, 1]
raw_acc = accuracy_score(y_test, raw_preds)
raw_brier = brier_score_loss(y_test, raw_probs)

print(f"\n  Base Extra Trees:")
print(f"    Accuracy:    {raw_acc*100:.2f}%")
print(f"    Brier Score: {raw_brier:.4f}")
print(f"\n  {classification_report(y_test, raw_preds, target_names=['DOWN', 'UP'])}")

# ══════════════════════════════════════════════════════════════════════════
# ISOTONIC CALIBRATION
# ══════════════════════════════════════════════════════════════════════════

print("-" * 60)
print("  Applying Isotonic Calibration")
print("-" * 60)

# Calibrate using cross-validation on training set
calibrated_model = CalibratedClassifierCV(base_model, method="isotonic", cv=5)
calibrated_model.fit(X_train, y_train)

cal_probs = calibrated_model.predict_proba(X_test)[:, 1]
cal_preds = (cal_probs >= 0.5).astype(int)
cal_acc = accuracy_score(y_test, cal_preds)
cal_brier = brier_score_loss(y_test, cal_probs)

print(f"\n  Calibrated Model:")
print(f"    Accuracy:    {cal_acc*100:.2f}%")
print(f"    Brier Score: {cal_brier:.4f} (was {raw_brier:.4f})")

# Calibration reliability
n_bins = 4
try:
    frac_pos, mean_pred = calibration_curve(y_test, cal_probs, n_bins=n_bins, strategy="uniform")
    print(f"\n  Calibration Check:")
    print(f"  {'Predicted':<12} {'Actual':<12} {'Gap':<8}")
    for p, a in zip(mean_pred, frac_pos):
        print(f"  {p*100:.1f}%{'':<8} {a*100:.1f}%{'':<8} {abs(p-a)*100:.1f}%")
except:
    print("  (Insufficient bins for calibration curve)")

# ══════════════════════════════════════════════════════════════════════════
# TRADE FILTERING ANALYSIS
# ══════════════════════════════════════════════════════════════════════════

print("\n" + "-" * 60)
print("  Confidence Threshold Analysis")
print("-" * 60)

max_conf = np.maximum(cal_probs, 1 - cal_probs)

print(f"\n  {'Threshold':<12} {'Trades':<10} {'Win Rate':<12} {'Signal %':<10}")
print("  " + "-" * 45)

for threshold in [0.55, 0.60, 0.65, 0.70, 0.75]:
    mask = max_conf >= threshold
    n_signals = mask.sum()
    if n_signals > 0:
        wr = accuracy_score(y_test[mask], cal_preds[mask]) * 100
        pct = n_signals / len(y_test) * 100
        print(f"  {threshold*100:.0f}%+{'':<8} {n_signals:<10} {wr:.1f}%{'':<7} {pct:.1f}%")
    else:
        print(f"  {threshold*100:.0f}%+{'':<8} 0{'':<10} --{'':<9} 0%")

# ══════════════════════════════════════════════════════════════════════════
# FEATURE IMPORTANCE (final model)
# ══════════════════════════════════════════════════════════════════════════

print("\n" + "-" * 60)
print("  Feature Importance (Final Model)")
print("-" * 60)

importances = pd.Series(base_model.feature_importances_, index=FEATURES).sort_values(ascending=False)
print()
for feat, imp in importances.items():
    bar = "█" * int(imp * 100)
    print(f"  {feat:18s} {imp:.4f} {bar}")

# ══════════════════════════════════════════════════════════════════════════
# SAVE MODEL
# ══════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("  Saving Calibrated Model")
print("=" * 60)

# Save the calibrated model (produces reliable probabilities)
joblib.dump(calibrated_model, MODEL_FILE)

print(f"\n  Model saved: {MODEL_FILE}")
print(f"  Type: CalibratedClassifierCV(ExtraTreesClassifier)")
print(f"  Features: {len(FEATURES)}")
print(f"  Target: {TARGET_HORIZON*5}min, {TARGET_THRESHOLD*100:.1f}% threshold")

# Also save metadata for the prediction system
metadata = {
    "features": FEATURES,
    "target_horizon": TARGET_HORIZON,
    "target_threshold": TARGET_THRESHOLD,
    "model_type": "CalibratedClassifierCV(ExtraTreesClassifier)",
    "walk_forward_accuracy": float(np.mean(wf_accuracies)),
    "walk_forward_wr60": float(np.mean(wf_win_rates_60)),
    "oos_accuracy": float(cal_acc),
    "brier_score": float(cal_brier),
    "n_features": len(FEATURES),
    "training_samples": len(X_train),
    "trained_at": pd.Timestamp.now().isoformat(),
}

metadata_path = MODEL_FILE.parent / "model_metadata.json"
import json
with open(metadata_path, "w") as f:
    json.dump(metadata, f, indent=2)

print(f"  Metadata: {metadata_path}")

print(f"""
  ┌─────────────────────────────────────────────────────┐
  │  TRAINING COMPLETE                                   │
  │                                                      │
  │  Walk-Forward Accuracy: {np.mean(wf_accuracies)*100:.1f}%                     │
  │  Walk-Forward WR@60%+: {np.mean(wf_win_rates_60)*100:.1f}%                      │
  │  OOS Accuracy:         {cal_acc*100:.1f}%                     │
  │  Brier Score:          {cal_brier:.4f}                   │
  │  Features:             {len(FEATURES)}                        │
  │  Calibration:          Isotonic (5-fold CV)           │
  └─────────────────────────────────────────────────────┘
""")
