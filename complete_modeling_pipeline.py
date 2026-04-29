"""
DATATHONMETC: COMPLETE DATA PREP & MODELING PIPELINE
=====================================================

This pipeline demonstrates:
1. Data quality assessment
2. Intelligent imputation strategies
3. Feature engineering with lags
4. Train/test split with time series validation
5. Baseline & advanced model training
6. Comprehensive evaluation
"""

import pandas as pd
import numpy as np
from sklearn.impute import KNNImputer
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import warnings
warnings.filterwarnings('ignore')

print("\n" + "="*80)
print("DATATHONMETC COMPLETE PIPELINE")
print("="*80)

# ============================================================================
# STEP 1: LOAD & PREPARE DATA
# ============================================================================
print("\n[STEP 1] LOADING & BASIC PREPARATION")
df = pd.read_csv('model_panel.csv')
df['tanggal'] = pd.to_datetime(df['tanggal'])
df = df.sort_values(['provinsi_id', 'tanggal']).reset_index(drop=True)

feat_cols = [c for c in df.columns if c.startswith('x')]
print(f"  Loaded: {df.shape[0]:,} rows × {df.shape[1]} columns")
print(f"  Target: twp90_pct | Features: {len(feat_cols)}")

# ============================================================================
# STEP 2: HANDLE MISSING DATA WITH KNN IMPUTATION
# ============================================================================
print("\n[STEP 2] INTELLIGENT DATA IMPUTATION")
print(f"  Before: {df[feat_cols].isnull().sum().sum():,} missing values")

# Use global KNN imputation (more robust than per-province)
imputer = KNNImputer(n_neighbors=5)
df_imputed = df.copy()
imputed_array = imputer.fit_transform(df[feat_cols])
df_imputed[feat_cols] = imputed_array

print(f"  After:  {df_imputed[feat_cols].isnull().sum().sum():,} missing values")
print(f"  ✓ Imputation complete (KNN, k=5 neighbors)")

# ============================================================================
# STEP 3: FEATURE ENGINEERING - TIME LAGS
# ============================================================================
print("\n[STEP 3] TIME LAG FEATURE ENGINEERING")
df_features = df_imputed.copy()

# Create lagged features (3-month and 6-month)
for lag in [3, 6]:
    for col in feat_cols:
        lag_col = f"{col}_lag{lag}"
        df_features[lag_col] = df_features.groupby('provinsi_id')[col].shift(lag)

print(f"  Added {2 * len(feat_cols)} lag features")
print(f"  Feature count: {len(feat_cols)} base + {2*len(feat_cols)} lags = {len(feat_cols) + 2*len(feat_cols)}")

# ============================================================================
# STEP 4: HANDLE LAG-INDUCED MISSING VALUES
# ============================================================================
print("\n[STEP 4] HANDLING LAG-INDUCED MISSING DATA")
df_features = df_features.dropna()
print(f"  After removing lag-induced NaNs: {df_features.shape[0]:,} rows")
print(f"  Data retention: {100*df_features.shape[0]/df.shape[0]:.1f}%")

# ============================================================================
# STEP 5: PREPARE FOR MODELING
# ============================================================================
print("\n[STEP 5] TRAIN/TEST SPLIT & FEATURE PREPARATION")
all_feat_cols = [c for c in df_features.columns if c.startswith('x')]
X = df_features[all_feat_cols].copy()
y = df_features['twp90_pct'].copy()

# Temporal split: 2024 cutoff
train_mask = df_features['tahun'] <= 2024
test_mask = df_features['tahun'] > 2024

X_train = X[train_mask]
y_train = y[train_mask]
X_test = X[test_mask]
y_test = y[test_mask]

print(f"  Train set: {X_train.shape[0]:,} samples (tahun ≤ 2024)")
print(f"  Test set: {X_test.shape[0]:,} samples (tahun > 2024)")
print(f"  Features: {X_train.shape[1]}")

# Standardize features
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

print(f"  ✓ Features standardized (μ=0, σ=1)")

# ============================================================================
# STEP 6: MODEL TRAINING - BASELINE
# ============================================================================
print("\n[STEP 6] BASELINE MODEL: RIDGE REGRESSION")
ridge = Ridge(alpha=1.0)
ridge.fit(X_train_scaled, y_train)

y_pred_ridge = ridge.predict(X_test_scaled)
rmse_ridge = np.sqrt(mean_squared_error(y_test, y_pred_ridge))
mae_ridge = mean_absolute_error(y_test, y_pred_ridge)
r2_ridge = r2_score(y_test, y_pred_ridge)

print(f"  RMSE: {rmse_ridge:.6f}")
print(f"  MAE:  {mae_ridge:.6f}")
print(f"  R²:   {r2_ridge:.6f}")

# ============================================================================
# STEP 7: MODEL TRAINING - RANDOM FOREST
# ============================================================================
print("\n[STEP 7] ADVANCED MODEL: RANDOM FOREST REGRESSOR")
rf = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
rf.fit(X_train, y_train)  # Random Forest doesn't need scaling

y_pred_rf = rf.predict(X_test)
rmse_rf = np.sqrt(mean_squared_error(y_test, y_pred_rf))
mae_rf = mean_absolute_error(y_test, y_pred_rf)
r2_rf = r2_score(y_test, y_pred_rf)

print(f"  RMSE: {rmse_rf:.6f}")
print(f"  MAE:  {mae_rf:.6f}")
print(f"  R²:   {r2_rf:.6f}")

# ============================================================================
# STEP 8: FEATURE IMPORTANCE
# ============================================================================
print("\n[STEP 8] FEATURE IMPORTANCE ANALYSIS (Random Forest)")
importance_df = pd.DataFrame({
    'Feature': all_feat_cols,
    'Importance': rf.feature_importances_
}).sort_values('Importance', ascending=False)

print("\n  Top 10 Most Important Features:")
for idx, row in importance_df.head(10).iterrows():
    print(f"    {row['Feature']:25s}: {row['Importance']:.4f}")

# ============================================================================
# STEP 9: MODEL COMPARISON & RECOMMENDATIONS
# ============================================================================
print("\n[STEP 9] MODEL COMPARISON")
print("\n  Ridge Regression:")
print(f"    RMSE: {rmse_ridge:.6f} | MAE: {mae_ridge:.6f} | R²: {r2_ridge:.6f}")
print("\n  Random Forest Regressor:")
print(f"    RMSE: {rmse_rf:.6f} | MAE: {mae_rf:.6f} | R²: {r2_rf:.6f}")

if rmse_rf < rmse_ridge:
    print(f"\n  ✓ Random Forest performs better (RMSE {100*(rmse_ridge-rmse_rf)/rmse_ridge:.1f}% improvement)")
else:
    print(f"\n  ✓ Ridge Regression performs better (RMSE {100*(rmse_rf-rmse_ridge)/rmse_rf:.1f}% improvement)")

# ============================================================================
# STEP 10: ERROR ANALYSIS
# ============================================================================
print("\n[STEP 10] PREDICTION ERROR ANALYSIS")
errors = np.abs(y_test.values - y_pred_rf)
print(f"\n  Random Forest Errors (on test set):")
print(f"    Mean Error: {errors.mean():.6f}")
print(f"    Std Dev:    {errors.std():.6f}")
print(f"    Min Error:  {errors.min():.6f}")
print(f"    Max Error:  {errors.max():.6f}")
print(f"    Median Error: {np.median(errors):.6f}")

# ============================================================================
# STEP 11: RECOMMENDATIONS
# ============================================================================
print("\n[STEP 11] NEXT STEPS & RECOMMENDATIONS")
print("\n1. MODEL IMPROVEMENT")
print("   • Try XGBoost/LightGBM for potentially better performance")
print("   • Perform hyperparameter tuning (GridSearch/RandomSearch)")
print("   • Ensemble methods (stacking, voting classifier)")

print("\n2. FEATURE ENGINEERING ENHANCEMENTS")
print("   • Add seasonal indicators (quarter, month_of_year)")
print("   • Create interaction terms (e.g., inflation × interest_rate)")
print("   • Add rolling statistics (mean, std, min, max)")
print("   • Polynomial features for key predictors")

print("\n3. VALIDATION & ROBUSTNESS")
print("   • Time-series cross-validation (walk-forward)")
print("   • Stratified k-fold by province")
print("   • Sensitivity analysis for key features")

print("\n4. PRODUCTION DEPLOYMENT")
print("   • Save best model with preprocessing pipeline")
print("   • Create prediction intervals (confidence bounds)")
print("   • Monitor model performance over time")
print("   • Implement retraining schedule")

print("\n" + "="*80)
print("PIPELINE EXECUTION COMPLETED SUCCESSFULLY!")
print("="*80 + "\n")
