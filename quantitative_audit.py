"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           JPTrades Quantitative Audit & Model Optimization                    ║
║                                                                             ║
║  PHASE 1: Feature Importance Analysis                                       ║
║  PHASE 2: Target Engineering                                                ║
║  PHASE 3: Model Evaluation                                                  ║
║  PHASE 4: Walk-Forward Validation                                           ║
║  PHASE 5: Confidence Calibration                                            ║
║  PHASE 6: Trade Filtering                                                   ║
║  PHASE 7: Options Intelligence                                              ║
║  PHASE 8: Performance Report                                                ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path

from sklearn.ensemble import (
    RandomForestClassifier, GradientBoostingClassifier, ExtraTreesClassifier
)
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    classification_report, brier_score_loss
)
from sklearn.model_selection import train_test_split
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.inspection import permutation_importance

try:
    from xgboost import XGBClassifier
    HAS_XGB = True
except ImportError:
    HAS_XGB = False

try:
    from lightgbm import LGBMClassifier
    HAS_LGBM = True
except ImportError:
    HAS_LGBM = False

from market_data import MarketData
from config import RANDOM_STATE

# ═══════════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════════

print("=" * 70)
print("  JPTrades QUANTITATIVE AUDIT")
print("  Objective: Maximize real out-of-sample predictive performance")
print("=" * 70)

print("\n[DATA] Loading market data...")
md = MarketData()
data = md.get_processed_data()
print(f"  Rows: {len(data)} | Date range: {data.index[0]} to {data.index[-1]}")

# Core features (no options - those are runtime only)
CORE_FEATURES = [
    "RSI", "EMA20", "EMA50", "EMA200", "EMA_DIFF", "PRICE_EMA20",
    "MACD", "MACD_SIGNAL", "MACD_HIST", "ATR",
    "BB_UPPER", "BB_LOWER", "BB_WIDTH",
    "RETURN_1", "RETURN_3", "RETURN_6",
    "BANK_CLOSE", "BANK_RETURN_1", "BANK_RETURN_3",
    "VIX_CLOSE", "VIX_RETURN_1", "VIX_RETURN_3",
    "HOUR", "MINUTE"
]

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1: FEATURE IMPORTANCE ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

print("\n" + "═" * 70)
print("  PHASE 1: FEATURE IMPORTANCE ANALYSIS")
print("═" * 70)

# Create baseline target for analysis
future_ret = (data["Close"].shift(-3) - data["Close"]) / data["Close"]
data_analysis = data.copy()
data_analysis["TARGET"] = None
data_analysis.loc[future_ret > 0.002, "TARGET"] = 1
data_analysis.loc[future_ret < -0.002, "TARGET"] = 0
data_analysis = data_analysis.dropna(subset=["TARGET"])
data_analysis["TARGET"] = data_analysis["TARGET"].astype(int)

X_all = data_analysis[CORE_FEATURES]
y_all = data_analysis["TARGET"]

# Time-ordered split
split_idx = int(len(X_all) * 0.8)
X_train_f, X_test_f = X_all.iloc[:split_idx], X_all.iloc[split_idx:]
y_train_f, y_test_f = y_all.iloc[:split_idx], y_all.iloc[split_idx:]

# Train a reference model
ref_model = GradientBoostingClassifier(
    n_estimators=200, learning_rate=0.05, max_depth=4, random_state=RANDOM_STATE
)
ref_model.fit(X_train_f, y_train_f)

# Built-in feature importance
feat_imp = pd.Series(ref_model.feature_importances_, index=CORE_FEATURES).sort_values(ascending=False)

print("\n  FEATURE IMPORTANCE (Gradient Boosting, built-in):")
print("  " + "-" * 50)
for feat, imp in feat_imp.items():
    bar = "█" * int(imp * 200)
    print(f"  {feat:20s} {imp:.4f} {bar}")

# Permutation importance (more reliable)
print("\n  PERMUTATION IMPORTANCE (on test set):")
print("  " + "-" * 50)
perm_imp = permutation_importance(ref_model, X_test_f, y_test_f, n_repeats=10, random_state=RANDOM_STATE)
perm_series = pd.Series(perm_imp.importances_mean, index=CORE_FEATURES).sort_values(ascending=False)

for feat, imp in perm_series.items():
    significance = "***" if imp > 0.005 else "**" if imp > 0.002 else "*" if imp > 0.001 else "  "
    print(f"  {significance} {feat:20s} {imp:.5f}")

# Correlation analysis
print("\n  HIGH CORRELATIONS (|r| > 0.85):")
print("  " + "-" * 50)
corr_matrix = X_all.corr()
high_corr_pairs = []
for i in range(len(corr_matrix)):
    for j in range(i+1, len(corr_matrix)):
        r = abs(corr_matrix.iloc[i, j])
        if r > 0.85:
            high_corr_pairs.append((corr_matrix.index[i], corr_matrix.columns[j], r))
            print(f"  {corr_matrix.index[i]:20s} ↔ {corr_matrix.columns[j]:20s} r={r:.3f}")

if not high_corr_pairs:
    print("  None found")

# Data leakage check
print("\n  DATA LEAKAGE CHECK:")
print("  " + "-" * 50)
leakage_suspects = []
for feat in CORE_FEATURES:
    corr_with_target = abs(data_analysis[feat].corr(data_analysis["TARGET"]))
    if corr_with_target > 0.5:
        leakage_suspects.append((feat, corr_with_target))
        print(f"  ⚠️  {feat}: r={corr_with_target:.3f} with TARGET (suspiciously high)")

if not leakage_suspects:
    print("  ✓ No features show suspicious correlation with target")

# Feature recommendations
print("\n  FEATURE RECOMMENDATIONS:")
print("  " + "-" * 50)

# Low importance features (permutation < 0.001)
low_value = [f for f, v in perm_series.items() if v < 0.001]
high_value = [f for f, v in perm_series.items() if v > 0.003]

print(f"  MOST VALUABLE:  {high_value}")
print(f"  LEAST VALUABLE: {low_value}")
print(f"  CONSIDER REMOVING: {[f for f, v in perm_series.items() if v < 0]}")


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2: TARGET ENGINEERING
# ═══════════════════════════════════════════════════════════════════════════════

print("\n\n" + "═" * 70)
print("  PHASE 2: TARGET ENGINEERING")
print("═" * 70)

horizons = [3, 6, 12]  # candles (15min, 30min, 60min)
thresholds = [0.001, 0.002, 0.003, 0.005]

print("\n  Testing target definitions (horizon × threshold):")
print(f"  {'Horizon':<12} {'Threshold':<12} {'Samples':<10} {'Balance':<12} {'OOS Accuracy':<15}")
print("  " + "-" * 65)

best_target = {"accuracy": 0, "horizon": 3, "threshold": 0.002}

for horizon in horizons:
    for threshold in thresholds:
        future_ret_h = (data["Close"].shift(-horizon) - data["Close"]) / data["Close"]
        
        df_temp = data.copy()
        df_temp["TGT"] = None
        df_temp.loc[future_ret_h > threshold, "TGT"] = 1
        df_temp.loc[future_ret_h < -threshold, "TGT"] = 0
        df_temp = df_temp.dropna(subset=["TGT"])
        df_temp["TGT"] = df_temp["TGT"].astype(int)
        
        if len(df_temp) < 100:
            continue
            
        X_t = df_temp[CORE_FEATURES]
        y_t = df_temp["TGT"]
        
        split = int(len(X_t) * 0.8)
        X_tr, X_te = X_t.iloc[:split], X_t.iloc[split:]
        y_tr, y_te = y_t.iloc[:split], y_t.iloc[split:]
        
        if len(X_te) < 20:
            continue
        
        m = GradientBoostingClassifier(
            n_estimators=150, learning_rate=0.05, max_depth=3, random_state=RANDOM_STATE
        )
        m.fit(X_tr, y_tr)
        acc = accuracy_score(y_te, m.predict(X_te))
        balance = y_t.mean()
        
        mins = horizon * 5
        print(f"  {mins}min{'':<8} {threshold*100:.1f}%{'':<9} {len(df_temp):<10} {balance:.2f}{'':<9} {acc*100:.2f}%")
        
        if acc > best_target["accuracy"]:
            best_target = {"accuracy": acc, "horizon": horizon, "threshold": threshold}

print(f"\n  BEST TARGET: {best_target['horizon']*5}min horizon, "
      f"{best_target['threshold']*100:.1f}% threshold "
      f"→ {best_target['accuracy']*100:.2f}% OOS accuracy")


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 3: MODEL EVALUATION
# ═══════════════════════════════════════════════════════════════════════════════

print("\n\n" + "═" * 70)
print("  PHASE 3: MODEL EVALUATION")
print("═" * 70)

# Use best target
best_h = best_target["horizon"]
best_th = best_target["threshold"]

future_ret_best = (data["Close"].shift(-best_h) - data["Close"]) / data["Close"]
data_model = data.copy()
data_model["TARGET"] = None
data_model.loc[future_ret_best > best_th, "TARGET"] = 1
data_model.loc[future_ret_best < -best_th, "TARGET"] = 0
data_model = data_model.dropna(subset=["TARGET"])
data_model["TARGET"] = data_model["TARGET"].astype(int)

X = data_model[CORE_FEATURES]
y = data_model["TARGET"]

split = int(len(X) * 0.8)
X_train, X_test = X.iloc[:split], X.iloc[split:]
y_train, y_test = y.iloc[:split], y.iloc[split:]

models = {
    "Random Forest": RandomForestClassifier(
        n_estimators=500, max_depth=8, min_samples_leaf=10, random_state=RANDOM_STATE, n_jobs=-1
    ),
    "Gradient Boosting": GradientBoostingClassifier(
        n_estimators=300, learning_rate=0.05, max_depth=4, 
        min_samples_leaf=10, random_state=RANDOM_STATE
    ),
    "Extra Trees": ExtraTreesClassifier(
        n_estimators=500, max_depth=8, min_samples_leaf=10, random_state=RANDOM_STATE, n_jobs=-1
    ),
}

if HAS_XGB:
    models["XGBoost"] = XGBClassifier(
        n_estimators=300, learning_rate=0.05, max_depth=4,
        min_child_weight=10, random_state=RANDOM_STATE, 
        use_label_encoder=False, eval_metric="logloss", verbosity=0
    )

if HAS_LGBM:
    models["LightGBM"] = LGBMClassifier(
        n_estimators=300, learning_rate=0.05, max_depth=4,
        min_child_samples=10, random_state=RANDOM_STATE, verbose=-1
    )

print(f"\n  Testing {len(models)} models on OOS data ({len(X_test)} samples):")
print(f"  {'Model':<20} {'Accuracy':<12} {'Precision':<12} {'Recall':<10} {'F1':<10} {'Brier':<10}")
print("  " + "-" * 70)

results = {}
for name, model in models.items():
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    probs = model.predict_proba(X_test)[:, 1]
    
    acc = accuracy_score(y_test, preds)
    prec = precision_score(y_test, preds, zero_division=0)
    rec = recall_score(y_test, preds, zero_division=0)
    f1 = f1_score(y_test, preds, zero_division=0)
    brier = brier_score_loss(y_test, probs)
    
    results[name] = {"accuracy": acc, "precision": prec, "recall": rec, "f1": f1, "brier": brier, "model": model}
    print(f"  {name:<20} {acc*100:.2f}%{'':<6} {prec*100:.2f}%{'':<6} {rec*100:.1f}%{'':<5} {f1:.3f}{'':<5} {brier:.4f}")

# Find best by F1 (balances precision and recall)
best_model_name = max(results, key=lambda k: results[k]["f1"])
print(f"\n  BEST MODEL: {best_model_name} (F1={results[best_model_name]['f1']:.3f})")


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 4: WALK-FORWARD VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

print("\n\n" + "═" * 70)
print("  PHASE 4: WALK-FORWARD VALIDATION")
print("═" * 70)

best_model_class = results[best_model_name]["model"].__class__
best_model_params = results[best_model_name]["model"].get_params()

# Walk-forward: train on expanding window, test on next segment
n_total = len(X)
fold_size = n_total // 5  # ~20% per fold
min_train_size = fold_size * 2  # Need at least 2 folds for training

wf_results = []
print(f"\n  Walk-forward folds (each ~{fold_size} samples):")
print(f"  {'Fold':<6} {'Train Size':<12} {'Test Size':<11} {'Accuracy':<11} {'Precision':<11} {'F1':<8} {'WinRate60+':<12}")
print("  " + "-" * 70)

for fold_start in range(min_train_size, n_total - fold_size, fold_size):
    fold_end = min(fold_start + fold_size, n_total)
    
    X_tr_wf = X.iloc[:fold_start]
    y_tr_wf = y.iloc[:fold_start]
    X_te_wf = X.iloc[fold_start:fold_end]
    y_te_wf = y.iloc[fold_start:fold_end]
    
    if len(X_te_wf) < 10:
        continue
    
    wf_model = best_model_class(**best_model_params)
    wf_model.fit(X_tr_wf, y_tr_wf)
    
    wf_preds = wf_model.predict(X_te_wf)
    wf_probs = wf_model.predict_proba(X_te_wf)
    
    wf_acc = accuracy_score(y_te_wf, wf_preds)
    wf_prec = precision_score(y_te_wf, wf_preds, zero_division=0)
    wf_f1 = f1_score(y_te_wf, wf_preds, zero_division=0)
    
    # Win rate for high-confidence predictions (>60%)
    high_conf_mask = np.max(wf_probs, axis=1) >= 0.60
    if high_conf_mask.sum() > 0:
        high_conf_acc = accuracy_score(y_te_wf[high_conf_mask], wf_preds[high_conf_mask])
    else:
        high_conf_acc = 0
    
    fold_num = len(wf_results) + 1
    wf_results.append({
        "accuracy": wf_acc, "precision": wf_prec, "f1": wf_f1, 
        "win_rate_60": high_conf_acc, "n_test": len(X_te_wf)
    })
    
    print(f"  {fold_num:<6} {len(X_tr_wf):<12} {len(X_te_wf):<11} "
          f"{wf_acc*100:.2f}%{'':<5} {wf_prec*100:.2f}%{'':<5} {wf_f1:.3f}{'':<4} "
          f"{high_conf_acc*100:.1f}%")

if wf_results:
    avg_acc = np.mean([r["accuracy"] for r in wf_results])
    avg_wr60 = np.mean([r["win_rate_60"] for r in wf_results])
    std_acc = np.std([r["accuracy"] for r in wf_results])
    print(f"\n  WALK-FORWARD AVERAGE: {avg_acc*100:.2f}% ± {std_acc*100:.2f}%")
    print(f"  HIGH-CONFIDENCE WIN RATE: {avg_wr60*100:.1f}%")


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 5: CONFIDENCE CALIBRATION
# ═══════════════════════════════════════════════════════════════════════════════

print("\n\n" + "═" * 70)
print("  PHASE 5: CONFIDENCE CALIBRATION")
print("═" * 70)

# Train calibrated model
best_raw_model = best_model_class(**best_model_params)
best_raw_model.fit(X_train, y_train)

raw_probs = best_raw_model.predict_proba(X_test)[:, 1]

# Calibrate using isotonic regression
cal_model = CalibratedClassifierCV(best_raw_model, method="isotonic", cv=3)
cal_model.fit(X_train, y_train)
cal_probs = cal_model.predict_proba(X_test)[:, 1]

# Compute calibration curves
n_bins = 5
raw_frac_pos, raw_mean_pred = calibration_curve(y_test, raw_probs, n_bins=n_bins, strategy="uniform")
cal_frac_pos, cal_mean_pred = calibration_curve(y_test, cal_probs, n_bins=n_bins, strategy="uniform")

print("\n  BEFORE CALIBRATION (raw model):")
print(f"  {'Predicted Conf':<18} {'Actual Win Rate':<18} {'Gap':<10}")
print("  " + "-" * 45)
for pred, actual in zip(raw_mean_pred, raw_frac_pos):
    gap = abs(pred - actual) * 100
    print(f"  {pred*100:.1f}%{'':<13} {actual*100:.1f}%{'':<13} {gap:.1f}%")

raw_brier = brier_score_loss(y_test, raw_probs)

print(f"\n  AFTER CALIBRATION (isotonic):")
print(f"  {'Predicted Conf':<18} {'Actual Win Rate':<18} {'Gap':<10}")
print("  " + "-" * 45)
for pred, actual in zip(cal_mean_pred, cal_frac_pos):
    gap = abs(pred - actual) * 100
    print(f"  {pred*100:.1f}%{'':<13} {actual*100:.1f}%{'':<13} {gap:.1f}%")

cal_brier = brier_score_loss(y_test, cal_probs)

print(f"\n  Brier Score (lower = better calibrated):")
print(f"    Raw:        {raw_brier:.4f}")
print(f"    Calibrated: {cal_brier:.4f}")
print(f"    Improvement: {((raw_brier - cal_brier) / raw_brier * 100):.1f}%")


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 6: TRADE FILTERING
# ═══════════════════════════════════════════════════════════════════════════════

print("\n\n" + "═" * 70)
print("  PHASE 6: TRADE FILTERING (Confidence Threshold Analysis)")
print("═" * 70)

# Use calibrated probabilities
confidence_levels = cal_probs  # Use calibrated
predictions = (cal_probs >= 0.5).astype(int)
max_conf = np.maximum(cal_probs, 1 - cal_probs)

print(f"\n  {'Conf Range':<15} {'Trades':<10} {'Win Rate':<12} {'Expectancy':<15} {'Profitable?':<12}")
print("  " + "-" * 65)

thresholds_to_test = [(0.50, 0.55), (0.55, 0.60), (0.60, 0.65), (0.65, 0.70), (0.70, 0.80), (0.80, 1.0)]

best_threshold = 0.60
best_expectancy = -999

for low, high in thresholds_to_test:
    mask = (max_conf >= low) & (max_conf < high)
    n_trades = mask.sum()
    
    if n_trades < 5:
        print(f"  {low*100:.0f}-{high*100:.0f}%{'':<9} {n_trades:<10} {'insufficient data':<12}")
        continue
    
    filtered_preds = predictions[mask]
    filtered_actual = y_test.values[mask]
    
    win_rate = accuracy_score(filtered_actual, filtered_preds) * 100
    
    # Simple expectancy: avg win% vs avg loss% on NIFTY direction
    # (In reality this should use option premium, but directional is our proxy here)
    wins = (filtered_preds == filtered_actual).sum()
    losses = n_trades - wins
    
    # Assuming average win = threshold% of premium, avg loss = SL%
    avg_win_return = 15.0  # ~15% avg option return on correct direction
    avg_loss_return = -8.0  # ~8% loss on wrong direction
    
    expectancy = (win_rate/100 * avg_win_return) + ((1 - win_rate/100) * avg_loss_return)
    profitable = "✓ YES" if expectancy > 0 else "✗ NO"
    
    print(f"  {low*100:.0f}-{high*100:.0f}%{'':<9} {n_trades:<10} {win_rate:.1f}%{'':<7} "
          f"{expectancy:+.2f}%{'':<9} {profitable}")
    
    if expectancy > best_expectancy:
        best_expectancy = expectancy
        best_threshold = low

print(f"\n  OPTIMAL THRESHOLD: {best_threshold*100:.0f}%+ confidence")
print(f"  Expected per-trade return: {best_expectancy:+.2f}%")


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 7: OPTIONS INTELLIGENCE
# ═══════════════════════════════════════════════════════════════════════════════

print("\n\n" + "═" * 70)
print("  PHASE 7: OPTIONS INTELLIGENCE")
print("═" * 70)

# Check if option features exist in data
option_features = ["ATM_STRIKE", "CE_LTP", "PE_LTP", "CE_PE_RATIO"]
available_opts = [f for f in option_features if f in data.columns]

if not available_opts:
    print("\n  Option features NOT present in training data.")
    print("  This is expected — options data comes from Angel One API at runtime only.")
    print("  Cannot evaluate option feature predictive power without historical option data.")
    print("\n  RECOMMENDATION: Collect option data over time into a CSV/DB,")
    print("  then re-run this analysis to determine if CE/PE momentum adds value.")
    print("  Until then, option data serves only as a trade execution aid (sentiment gauge),")
    print("  NOT as a prediction input.")
else:
    # If options are somehow in the data, test their contribution
    X_with_opts = data_model[CORE_FEATURES + available_opts]
    X_tr_o, X_te_o = X_with_opts.iloc[:split], X_with_opts.iloc[split:]
    
    m_opts = GradientBoostingClassifier(
        n_estimators=200, learning_rate=0.05, max_depth=4, random_state=RANDOM_STATE
    )
    m_opts.fit(X_tr_o, y_train)
    acc_with = accuracy_score(y_test, m_opts.predict(X_te_o))
    acc_without = results[best_model_name]["accuracy"]
    
    print(f"\n  Without options: {acc_without*100:.2f}%")
    print(f"  With options:    {acc_with*100:.2f}%")
    print(f"  Difference:      {(acc_with - acc_without)*100:+.2f}%")
    
    if acc_with > acc_without + 0.005:
        print("  → Options features ADD predictive value")
    else:
        print("  → Options features do NOT add significant predictive value")


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 8: PERFORMANCE REPORT
# ═══════════════════════════════════════════════════════════════════════════════

print("\n\n" + "═" * 70)
print("  PHASE 8: FINAL PERFORMANCE REPORT")
print("═" * 70)

# Current system accuracy (baseline)
baseline_model = GradientBoostingClassifier(
    n_estimators=200, random_state=RANDOM_STATE
)
# Original target: 3 candles, 0.2%
future_ret_orig = (data["Close"].shift(-3) - data["Close"]) / data["Close"]
data_orig = data.copy()
data_orig["TARGET"] = None
data_orig.loc[future_ret_orig > 0.002, "TARGET"] = 1
data_orig.loc[future_ret_orig < -0.002, "TARGET"] = 0
data_orig = data_orig.dropna(subset=["TARGET"])
data_orig["TARGET"] = data_orig["TARGET"].astype(int)
X_orig = data_orig[CORE_FEATURES]
y_orig = data_orig["TARGET"]
s_orig = int(len(X_orig) * 0.8)
baseline_model.fit(X_orig.iloc[:s_orig], y_orig.iloc[:s_orig])
baseline_acc = accuracy_score(y_orig.iloc[s_orig:], baseline_model.predict(X_orig.iloc[s_orig:]))

print(f"""
  ┌─────────────────────────────────────────────────────────────────────┐
  │  CURRENT vs RECOMMENDED                                             │
  ├──────────────────────────┬──────────────────┬───────────────────────┤
  │  Metric                  │  Current         │  Recommended          │
  ├──────────────────────────┼──────────────────┼───────────────────────┤
  │  OOS Accuracy            │  {baseline_acc*100:.2f}%          │  {best_target['accuracy']*100:.2f}%              │
  │  Target Horizon          │  15 min (3 bars) │  {best_target['horizon']*5} min ({best_target['horizon']} bars)         │
  │  Move Threshold          │  0.2%            │  {best_target['threshold']*100:.1f}%               │
  │  Best Model              │  Random Forest   │  {best_model_name:<22}│
  │  Walk-Forward Avg        │  unknown         │  {avg_acc*100:.2f}% ± {std_acc*100:.2f}%       │
  │  Calibration (Brier)     │  {raw_brier:.4f}         │  {cal_brier:.4f}              │
  │  Optimal Conf Threshold  │  60%             │  {best_threshold*100:.0f}%                  │
  │  Expected Expectancy     │  unknown         │  {best_expectancy:+.2f}%/trade          │
  └──────────────────────────┴──────────────────┴───────────────────────┘
""")

print("  KEY FINDINGS:")
print("  " + "-" * 60)
print(f"  1. Best target: {best_target['horizon']*5}-minute horizon with {best_target['threshold']*100:.1f}% threshold")
print(f"  2. Best model: {best_model_name} (F1={results[best_model_name]['f1']:.3f})")
print(f"  3. Calibration improves Brier score by {((raw_brier - cal_brier) / raw_brier * 100):.1f}%")
print(f"  4. Optimal confidence filter: {best_threshold*100:.0f}%+")

if high_value:
    print(f"  5. Most predictive features: {', '.join(high_value[:5])}")
if low_value:
    print(f"  6. Low-value features (consider removing): {', '.join(low_value[:5])}")

print(f"\n  FEATURES CURRENTLY USED: {len(CORE_FEATURES)}")
recommended_features = [f for f in CORE_FEATURES if perm_series.get(f, 0) >= 0]
print(f"  RECOMMENDED FEATURES:    {len(recommended_features)}")
removed = [f for f in CORE_FEATURES if f not in recommended_features]
if removed:
    print(f"  FEATURES TO REMOVE:      {removed}")

print("\n  MODELS TESTED:")
for name, r in sorted(results.items(), key=lambda x: x[1]["f1"], reverse=True):
    print(f"    {name:<20} F1={r['f1']:.3f}  Acc={r['accuracy']*100:.2f}%  Brier={r['brier']:.4f}")

print(f"""
  ┌─────────────────────────────────────────────────────────────────────┐
  │  RECOMMENDATIONS                                                     │
  ├─────────────────────────────────────────────────────────────────────┤
  │  1. Switch to {best_model_name} as primary model{' ' * (38 - len(best_model_name))}│
  │  2. Use {best_target['horizon']*5}-min horizon with {best_target['threshold']*100:.1f}% threshold{' ' * 28}│
  │  3. Apply isotonic calibration to all probabilities               │
  │  4. Only trade when calibrated confidence >= {best_threshold*100:.0f}%{' ' * 17}│
  │  5. Track option premium P&L (not just direction){' ' * 18}│
  │  6. Use walk-forward validation for model updates{' ' * 18}│
  └─────────────────────────────────────────────────────────────────────┘
""")

print("=" * 70)
print("  AUDIT COMPLETE")
print("=" * 70)
