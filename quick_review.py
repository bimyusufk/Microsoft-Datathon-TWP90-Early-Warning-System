import pandas as pd
import numpy as np

# Load data
df = pd.read_csv('model_panel.csv')

# Basic stats
print("\n" + "="*80)
print("DATA PREPARATION & MODELING REVIEW - DATATHONMETC")
print("="*80)

print(f"\n[1] DATASET OVERVIEW")
print(f"  Shape: {df.shape[0]:,} rows × {df.shape[1]} columns")
print(f"  Columns: {', '.join(df.columns[:7])}...")

print(f"\n[2] TEMPORAL COVERAGE")
print(f"  Date range: {df['tanggal'].min()} to {df['tanggal'].max()}")
print(f"  Years: {sorted(df['tahun'].unique())}")

print(f"\n[3] GEOGRAPHIC COVERAGE")
print(f"  Provinces: {df['provinsi_id'].nunique()}")

print(f"\n[4] TARGET VARIABLE (twp90_pct)")
print(f"  Non-null: {df['twp90_pct'].notna().sum():,} / {len(df):,}")
print(f"  Mean: {df['twp90_pct'].mean():.6f}")
print(f"  Std: {df['twp90_pct'].std():.6f}")
print(f"  Min: {df['twp90_pct'].min():.6f}")
print(f"  Max: {df['twp90_pct'].max():.6f}")

print(f"\n[5] FEATURE VARIABLES (x1-x10)")
feat_cols = [c for c in df.columns if c.startswith('x')]
for col in feat_cols:
    pct_complete = 100 * df[col].notna().sum() / len(df)
    print(f"  {col:20s}: {pct_complete:5.1f}% complete | μ={df[col].mean():12.2f} σ={df[col].std():12.2f}")

print(f"\n[6] MISSING DATA ANALYSIS")
total_missing = df[feat_cols + ['twp90_pct']].isnull().sum().sum()
total_cells = len(df) * (len(feat_cols) + 1)
completeness = 100 * (1 - total_missing / total_cells)
print(f"  Total missing: {total_missing:,} / {total_cells:,}")
print(f"  Completeness: {completeness:.1f}%")

print(f"\n[7] COMPLETE CASES (for modeling)")
df_clean = df[feat_cols + ['twp90_pct']].dropna()
print(f"  Complete rows: {len(df_clean):,} / {len(df):,}")
print(f"  Usable %: {100*len(df_clean)/len(df):.1f}%")

print(f"\n[8] TRAIN/TEST SPLIT (Temporal)")
df_temp = df[df['tahun'].notna()]
train = df_temp[df_temp['tahun'] <= 2024]
test = df_temp[df_temp['tahun'] > 2024]
print(f"  Train (2022-2024): {len(train):,} rows")
print(f"  Test (2025+): {len(test):,} rows")

print(f"\n[9] DATA QUALITY ASSESSMENT")
print(f"  ✓ Temporal continuity: {sorted(df['tahun'].unique())}")
print(f"  ✓ Geographic diversity: {df['provinsi_id'].nunique()} provinces")
print(f"  ✓ Target coverage: {100*df['twp90_pct'].notna().sum()/len(df):.1f}%")

print("\n" + "="*80)
print("RECOMMENDATIONS:")
print("="*80)
print("\n1. DATA IMPUTATION")
print("   - Use KNN imputation (k=5) for missing features")
print("   - Or use forward-fill by province for time series")

print("\n2. FEATURE ENGINEERING")
print("   - Add time lags (t-1, t-3, t-6)")
print("   - Add rolling statistics (3-month, 6-month windows)")
print("   - Normalize/standardize features")

print("\n3. MODELING APPROACH")
print("   - Start with gradient boosting (XGBoost, LightGBM)")
print("   - Use temporal train/test split (2024 as cutoff)")
print("   - Evaluate with RMSE, MAE, R² metrics")

print("\n4. VALIDATION STRATEGY")
print("   - Time-series cross-validation (avoid data leakage)")
print("   - Stratified by province if needed")
print("   - Out-of-time validation on 2025 data")

print("\n" + "="*80 + "\n")
