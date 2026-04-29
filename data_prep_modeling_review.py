"""
COMPREHENSIVE DATA PREPARATION & MODELING REVIEW
DatathonMETC Project
=====================================================

This script performs a full review of the data preparation pipeline
and provides recommendations for the modeling phase.
"""

import pandas as pd
import numpy as np
import os
from pathlib import Path

# Configuration
PROJECT_DIR = Path("c:\\Users\\bimyu\\Documents\\Projects\\DatathonMETC")
MODEL_PANEL_CSV = PROJECT_DIR / "model_panel.csv"
DB_PATH = PROJECT_DIR / "datathon.db"

print("=" * 80)
print("DATATHONMETC: KOMPREHENSIF DATA PREP & MODELING REVIEW")
print("=" * 80)

# ============================================================================
# PHASE 1: LOAD & INSPECT DATA
# ============================================================================
print("\n[PHASE 1] LOADING & INSPECTING DATA")
print("-" * 80)

if MODEL_PANEL_CSV.exists():
    df = pd.read_csv(MODEL_PANEL_CSV)
    print(f"✓ Model panel loaded: {df.shape[0]:,} rows × {df.shape[1]} columns")
    print(f"\nColumns: {df.columns.tolist()}")
else:
    print(f"✗ Model panel not found at {MODEL_PANEL_CSV}")
    exit(1)

# ============================================================================
# PHASE 2: DATA QUALITY ASSESSMENT
# ============================================================================
print("\n[PHASE 2] DATA QUALITY ASSESSMENT")
print("-" * 80)

print(f"\n2.1 TEMPORAL COVERAGE")
print(f"  Date range: {df['tanggal'].min()} to {df['tanggal'].max()}")
print(f"  Year range: {df['tahun'].min()} to {df['tahun'].max()}")
print(f"  Unique years: {sorted(df['tahun'].unique())}")
print(f"  Unique months per year: {df.groupby('tahun')['bulan'].nunique().to_dict()}")

print(f"\n2.2 GEOGRAPHICAL COVERAGE")
print(f"  Total provinces: {df['provinsi_id'].nunique()}")
print(f"  Province names: {sorted(df['nama_provinsi'].unique())[:5]}... ({len(df['nama_provinsi'].unique())} total)")

print(f"\n2.3 TARGET VARIABLE (twp90_pct) ANALYSIS")
target = df['twp90_pct']
print(f"  Non-null count: {target.notna().sum():,} / {len(target):,} ({100*target.notna().sum()/len(target):.1f}%)")
print(f"  Missing count: {target.isna().sum():,}")
print(f"  Mean: {target.mean():.6f}")
print(f"  Std Dev: {target.std():.6f}")
print(f"  Min: {target.min():.6f}")
print(f"  Max: {target.max():.6f}")
print(f"  Median: {target.median():.6f}")

print(f"\n2.4 FEATURE VARIABLES (x1-x10) ANALYSIS")
feature_cols = [c for c in df.columns if c.startswith('x')]
print(f"  Total features: {len(feature_cols)}")

for col in feature_cols:
    null_pct = 100 * df[col].isna().sum() / len(df)
    mean_val = df[col].mean()
    std_val = df[col].std()
    print(f"  {col:20s}: {(100-null_pct):5.1f}% data | μ={mean_val:12.2f} σ={std_val:12.2f}")

# ============================================================================
# PHASE 3: MISSING DATA PATTERN ANALYSIS
# ============================================================================
print("\n[PHASE 3] MISSING DATA PATTERN ANALYSIS")
print("-" * 80)

print("\n3.1 MISSING DATA BY FEATURE")
missing_by_feature = df[feature_cols].isnull().sum().sort_values(ascending=False)
for col, count in missing_by_feature.items():
    if count > 0:
        pct = 100 * count / len(df)
        print(f"  {col:20s}: {count:5d} missing ({pct:5.1f}%)")

print("\n3.2 MISSING DATA PATTERN BY PROVINCE")
missing_by_prov = df.groupby('nama_provinsi')[feature_cols].isnull().sum().sum(axis=1).sort_values(ascending=False)
print(f"  Provinces with most missing values:")
for prov, count in missing_by_prov.head(10).items():
    print(f"    {prov:25s}: {count:5d} missing values")

print("\n3.3 DATA COMPLETENESS SCORE")
completeness = 100 * (1 - df[feature_cols + ['twp90_pct']].isnull().sum().sum() / (len(df) * (len(feature_cols) + 1)))
print(f"  Overall data completeness: {completeness:.1f}%")

# ============================================================================
# PHASE 4: DISTRIBUTION & OUTLIER ANALYSIS
# ============================================================================
print("\n[PHASE 4] DISTRIBUTION & OUTLIER ANALYSIS")
print("-" * 80)

def detect_outliers_iqr(series, k=1.5):
    """Detect outliers using IQR method"""
    Q1 = series.quantile(0.25)
    Q3 = series.quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - k * IQR
    upper_bound = Q3 + k * IQR
    return (series < lower_bound) | (series > upper_bound)

print("\n4.1 OUTLIERS (IQR Method, k=1.5)")
for col in feature_cols:
    if df[col].notna().sum() > 0:
        outliers = detect_outliers_iqr(df[col])
        outlier_count = outliers.sum()
        if outlier_count > 0:
            pct = 100 * outlier_count / df[col].notna().sum()
            print(f"  {col:20s}: {outlier_count:3d} outliers ({pct:.1f}% of non-null values)")

print("\n4.2 TARGET VARIABLE DISTRIBUTION")
target_outliers = detect_outliers_iqr(df['twp90_pct'])
print(f"  Outliers in twp90_pct: {target_outliers.sum()} ({100*target_outliers.sum()/len(df):.1f}%)")
print(f"  Skewness: {df['twp90_pct'].skew():.3f}")
print(f"  Kurtosis: {df['twp90_pct'].kurtosis():.3f}")

# ============================================================================
# PHASE 5: CORRELATION ANALYSIS
# ============================================================================
print("\n[PHASE 5] CORRELATION ANALYSIS")
print("-" * 80)

print("\n5.1 CORRELATION WITH TARGET VARIABLE")
corr_data = df[feature_cols + ['twp90_pct']].copy()
correlations = corr_data.corr()['twp90_pct'].drop('twp90_pct').sort_values(ascending=False)
for col, corr_val in correlations.items():
    if not np.isnan(corr_val):
        strength = "Strong" if abs(corr_val) > 0.7 else "Moderate" if abs(corr_val) > 0.3 else "Weak"
        print(f"  {col:20s}: {corr_val:7.3f} ({strength})")

print("\n5.2 FEATURE MULTICOLLINEARITY (Top Correlations)")
corr_matrix = corr_data.corr()
# Get upper triangle to avoid duplicates
upper_triangle = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
correlations_sorted = []
for col in upper_triangle.columns:
    for idx in upper_triangle.index:
        val = upper_triangle.loc[idx, col]
        if not np.isnan(val) and abs(val) > 0.7:
            correlations_sorted.append((col, idx, val))

correlations_sorted.sort(key=lambda x: abs(x[2]), reverse=True)
for col1, col2, val in correlations_sorted[:10]:
    print(f"  {col1:20s} <--> {col2:20s}: {val:7.3f}")

# ============================================================================
# PHASE 6: MODEL READINESS ASSESSMENT
# ============================================================================
print("\n[PHASE 6] MODEL READINESS ASSESSMENT")
print("-" * 80)

print("\n6.1 DATA SUFFICIENCY FOR MODELING")
df_clean = df[feature_cols + ['twp90_pct']].dropna()
print(f"  Complete cases (no missing values): {len(df_clean):,} ({100*len(df_clean)/len(df):.1f}%)")
print(f"  Data loss due to listwise deletion: {100*(1-len(df_clean)/len(df)):.1f}%")

print("\n6.2 TRAIN/TEST SPLIT FEASIBILITY (Temporal)")
years_unique = sorted(df_clean['tahun'].unique())
print(f"  Unique years with complete data: {years_unique}")
train_cutoff = 2024
test_years = [y for y in years_unique if y > train_cutoff]
print(f"  Proposed: Train (tahun <= {train_cutoff}), Test (tahun > {train_cutoff})")
print(f"  Train samples: {len(df_clean[df_clean['tahun'] <= train_cutoff]):,}")
print(f"  Test samples: {len(df_clean[df_clean['tahun'] > train_cutoff]):,}")

print("\n6.3 CLASS BALANCE (for regression)")
print(f"  Target variable range: [{target.min():.4f}, {target.max():.4f}]")
print(f"  Quantile distribution:")
print(f"    Q1 (25%): {target.quantile(0.25):.4f}")
print(f"    Q2 (50%): {target.quantile(0.50):.4f}")
print(f"    Q3 (75%): {target.quantile(0.75):.4f}")

# ============================================================================
# PHASE 7: RECOMMENDATIONS
# ============================================================================
print("\n[PHASE 7] RECOMMENDATIONS & NEXT STEPS")
print("-" * 80)

recommendations = []

# Check completeness
if completeness < 80:
    recommendations.append(f"• Data completeness is {completeness:.1f}% - Consider imputation strategy")
    recommendations.append("  Options: KNN imputation, forward-fill by province, median imputation")

# Check outliers
outlier_count = sum(detect_outliers_iqr(df[col]).sum() for col in feature_cols if df[col].notna().sum() > 0)
if outlier_count > len(df) * 0.05:
    recommendations.append(f"• Detected {outlier_count:,} outliers - Consider:")
    recommendations.append("  - Robust scaling (e.g., RobustScaler)")
    recommendations.append("  - Winsorization for extreme values")

# Check multicollinearity
high_corr = len([c for c in correlations_sorted if abs(c[2]) > 0.9])
if high_corr > 0:
    recommendations.append(f"• {high_corr} feature pairs highly correlated - Consider:")
    recommendations.append("  - PCA for dimensionality reduction")
    recommendations.append("  - Feature selection (remove redundant features)")

# Check missing data
if len(df_clean) / len(df) < 0.7:
    recommendations.append(f"• Only {100*len(df_clean)/len(df):.1f}% complete cases - Consider:")
    recommendations.append("  - KNN imputation (k=5)")
    recommendations.append("  - MICE (Multivariate Imputation by Chained Equations)")

# Check temporal distribution
if len(test_years) < 3:
    recommendations.append(f"• Limited test periods ({len(test_years)}) - Consider:")
    recommendations.append("  - K-Fold cross-validation (stratified by province)")
    recommendations.append("  - Rolling window validation")

if not recommendations:
    recommendations.append("✓ Data is well-prepared for modeling!")

print("\n" + "\n".join(recommendations))

# ============================================================================
# PHASE 8: MODELING SUGGESTIONS
# ============================================================================
print("\n[PHASE 8] SUGGESTED MODELING APPROACHES")
print("-" * 80)

print("\n8.1 BASELINE MODELS")
print("  • Linear Regression (OLS) - fast baseline")
print("  • Ridge Regression - handles multicollinearity")
print("  • Decision Tree - non-linear baseline")

print("\n8.2 GRADIENT BOOSTING MODELS (Recommended)")
print("  • XGBoost - fast, efficient, handles missing data")
print("  • LightGBM - lightweight, faster training")
print("  • CatBoost - good for categorical features")

print("\n8.3 ADVANCED APPROACHES")
print("  • Random Forest Regressor - feature importance, robust")
print("  • Neural Networks - if sufficient data and features engineered")
print("  • Ensemble Methods - combine multiple models for better predictions")

print("\n8.4 FEATURE ENGINEERING SUGGESTIONS")
print("  • Time lags (t-1, t-3, t-6 months)")
print("  • Rolling statistics (3-month, 6-month windows)")
print("  • Trend decomposition (trend, seasonal components)")
print("  • Interaction features (e.g., inflation × interest rate)")
print("  • Polynomial features for key variables")

print("\n8.5 EVALUATION METRICS")
print("  • RMSE (Root Mean Squared Error) - main metric")
print("  • MAE (Mean Absolute Error) - interpretability")
print("  • R² Score - proportion of variance explained")
print("  • MAPE (Mean Absolute Percentage Error) - for business context")

# ============================================================================
# PHASE 9: PIPELINE EXECUTION CHECKLIST
# ============================================================================
print("\n[PHASE 9] MODELING PIPELINE CHECKLIST")
print("-" * 80)

checklist = [
    ("✓" if completeness > 70 else "⚠", "Data completeness check (target: >70%)"),
    ("✓" if len(df_clean) > 100 else "✗", "Sufficient training samples (target: >100)"),
    ("✓" if len(test_years) >= 1 else "⚠", "Test set availability"),
    ("✓" if len(missing_by_feature[missing_by_feature > 0]) <= 3 else "⚠", "Limited missing data patterns"),
    ("✓" if outlier_count < len(df) * 0.1 else "⚠", "Outliers within acceptable range"),
    ("✓" if high_corr <= 5 else "⚠", "Multicollinearity within acceptable range"),
]

for status, item in checklist:
    print(f"  {status} {item}")

# ============================================================================
# FINAL SUMMARY
# ============================================================================
print("\n" + "=" * 80)
print("SUMMARY STATISTICS")
print("=" * 80)

summary_stats = {
    "Total Records": len(df),
    "Complete Cases": len(df_clean),
    "Completeness %": completeness,
    "Features": len(feature_cols),
    "Provinces": df['provinsi_id'].nunique(),
    "Time Span (months)": df['tahun'].nunique() * 12,
    "Target Mean": df['twp90_pct'].mean(),
    "Target Std Dev": df['twp90_pct'].std(),
}

for key, value in summary_stats.items():
    if isinstance(value, float):
        print(f"  {key:.<40} {value:>15.2f}")
    else:
        print(f"  {key:.<40} {value:>15}")

print("\n" + "=" * 80)
print("✓ Data preparation and modeling review completed successfully!")
print("=" * 80)
