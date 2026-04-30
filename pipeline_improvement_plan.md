# 🗺️ Rencana Perbaikan Pipeline — TWP90 Early Warning System

> Berdasarkan: Deep Technical Audit (2026-04-30)  
> Status iterasi: Belum dimulai — akan dievaluasi satu per satu

---

## 📊 Peta Aset Data (Realistis)

Sebelum menentukan pipeline, petakan dulu apa yang benar-benar tersedia:

| Fitur | Granularity Asli | Frekuensi Real | Bisa digunakan bulanan? |
|-------|-----------------|----------------|------------------------|
| `twp90_pct` | Bulanan per provinsi | ✅ Bulanan | ✅ Ya |
| `x1_bi_rate_pct` | Bulanan nasional | ✅ Bulanan | ✅ Ya (tanpa variasi provinsi) |
| `x2_inflasi_yoy` | Bulanan per provinsi | ✅ Bulanan | ✅ Ya |
| `x3_pdrb_per_kapita` | Tahunan per provinsi | ❌ Tahunan | ⚠️ Hanya sbg annual proxy |
| `x4_tpt_pct` | Semesteran (Feb & Agt) | ❌ Semesteran | ⚠️ Interpolasi linear saja |
| `x5_penetrasi_internet` | Tahunan per provinsi | ❌ Tahunan | ⚠️ Hanya sbg annual proxy |
| `x6_tabungan_miliar` | Tahunan per provinsi | ❌ Tahunan | ⚠️ Hanya sbg annual proxy |
| `x7_jumlah_kc_bank` | Tahunan per provinsi | ❌ Tahunan | ⚠️ Hanya sbg annual proxy |
| `x8_ldr_pct` | Tahunan per provinsi | ❌ Tahunan | ⚠️ Hanya sbg annual proxy |
| `x9_npl_ratio` | Tahunan per provinsi | ❌ Tahunan | ⚠️ Hanya sbg annual proxy |
| `x10_rasio_umkm` | Tahunan per provinsi | ❌ Tahunan | ⚠️ Hanya sbg annual proxy |

**Kesimpulan**: Hanya 3 fitur yang benar-benar bulanan (twp90, bi_rate, inflasi). Sisanya annual.

---

## 🔧 TRACK 0 — Perbaikan Pipeline Existing (Fix-First)

> **Tujuan**: Perbaiki flaw kritis di pipeline yang ada sebelum mencoba arsitektur baru  
> **Kompleksitas**: Rendah | **Prioritas**: PERTAMA

### Perubahan yang Harus Dilakukan

#### Fix 1 — Hapus PCHIP Smoothing `[2.1_data_cleaning_smoothing.ipynb]`

**Masalah**: PCHIP membuat data sintetis antar titik tahunan  
**Perbaikan**: Ganti dengan forward-carry sederhana (step function) yang jujur

```python
# HAPUS blok apply_true_spline() sepenuhnya
# Ganti dengan forward-carry per provinsi, tanpa interpolasi antar tahun

for col in annual_cols:  # x3, x5, x6, x7, x8, x9, x10
    df[col] = df.groupby('provinsi_id')[col].ffill()
```

> Alasan: Step function jujur apa adanya. Model harus tahu bahwa PDRB tidak berubah tiap bulan.

#### Fix 2 — Perbaiki Imputasi x4_tpt_pct `[2.1_data_cleaning_smoothing.ipynb]`

**Masalah**: ffill(5) mengasumsikan pengangguran konstan 5 bulan  
**Perbaikan**: Interpolasi linear antara Feb dan Agt (hanya 6 titik per tahun)

```python
# Interpolasi linear antara titik semesteran per provinsi
df['x4_tpt_pct'] = (
    df.groupby('provinsi_id')['x4_tpt_pct']
    .transform(lambda s: s.interpolate(method='linear', limit_direction='both'))
)
```

#### Fix 3 — Tambah Fitur Waktu & Provinsi `[2.2_feature_engineering.ipynb]`

**Masalah**: Model tidak tahu panel structure  
**Perbaikan**: Tambahkan fitur identitas

```python
# Tambahkan fitur time dan panel identity
df['bulan_sin'] = np.sin(2 * np.pi * df['bulan'] / 12)  # seasonality encoding
df['bulan_cos'] = np.cos(2 * np.pi * df['bulan'] / 12)
df['time_trend'] = df.groupby('provinsi_id').cumcount()  # trend linear

# Province dummy (untuk model tanpa fixed-effects)
df = pd.get_dummies(df, columns=['provinsi_id'], prefix='prov', drop_first=True)
```

#### Fix 4 — Tambah Baseline & Train Metrics `[3.1_model_training.ipynb]`

**Masalah**: Tidak ada baseline, tidak ada train error  
**Perbaikan**:

```python
# Naive baseline: prediksi = nilai bulan sebelumnya (per provinsi)
test_data['naive_pred'] = test_data.groupby('provinsi_id')['y_true'].shift(1).fillna(method='ffill')
rmse_naive = sqrt(mean_squared_error(test_data['y_true'], test_data['naive_pred']))

# Train metrics (untuk deteksi overfitting)
y_train_pred = model.predict(X_train)
rmse_train = sqrt(mean_squared_error(y_train, y_train_pred))
print(f'RMSE Train: {rmse_train:.4f} | RMSE Test: {rmse_test:.4f} | RMSE Naive: {rmse_naive:.4f}')
```

#### Fix 5 — Perbaiki Feature Importance Calculation

**Masalah**: Importance dikelompokkan per `x_base`, menyembunyikan lag version yang lebih penting  
**Perbaikan**: Tampilkan semua fitur, termasuk full breakdown lag vs non-lag

### Metrik Evaluasi Fix-Pipeline

| Metrik | Target |
|--------|--------|
| R² (test) | Seharusnya **turun** dari 0.42 (karena kita menghapus data artifisial) |
| RMSE test vs RMSE naive | RMSE model harus < RMSE naive |
| RMSE train vs RMSE test | Gap < 30% (tidak overfitting) |

---

## 🅰️ PIPELINE A — Annual Panel Regression (Econometric Baseline)

> **Filosofi**: Jujur dengan data. Kalau datanya tahunan, model pun harus tahunan.  
> **Kompleksitas**: Rendah | **Prioritas**: KEDUA (setelah Fix)

### Arsitektur

```
model_panel.csv
    │
    ▼ [A.1 Aggregate]
Annual panel: 31 provinsi × 5 tahun = 155 observasi
Target: rata-rata twp90_pct per tahun per provinsi
    │
    ▼ [A.2 Feature Set]
Fitur: x3_pdrb, x4_tpt (avg Feb+Agt), x5–x10, avg(x1_bi_rate), avg(x2_inflasi)
    │
    ▼ [A.3 Split]
Train: 2021–2023 (93 obs) | Test: 2024–2025 (62 obs)
    │
    ▼ [A.4 Model: Panel Fixed Effects OLS]
twp90_avg ~ x1_avg + x2_avg + ... + province_FE + year_FE
    │
    ▼ [A.5 Evaluasi]
R², RMSE, koefisien interpretabel, VIF, residual plot
```

### Implementasi

```python
# A.3 — Annual aggregation
df_annual = df.groupby(['provinsi_id', 'tahun']).agg(
    twp90_avg=('twp90_pct', 'mean'),
    x1_avg=('x1_bi_rate_pct', 'mean'),
    x2_avg=('x2_inflasi_yoy', 'mean'),
    x3=('x3_pdrb_per_kapita', 'first'),   # ambil nilai tahunan
    x4_avg=('x4_tpt_pct', 'mean'),         # avg dari 2 semester
    x5=('x5_penetrasi_internet_pct', 'first'),
    x6=('x6_tabungan_miliar', 'first'),
    x7=('x7_jumlah_kc_bank', 'first'),
    x8=('x8_ldr_pct', 'first'),
    x9=('x9_npl_ratio', 'first'),
    x10=('x10_rasio_umkm', 'first'),
).reset_index()

# A.4 — Fixed Effects via dummy variables (LSDV approach)
import statsmodels.formula.api as smf

formula = 'twp90_avg ~ x1_avg + x2_avg + np.log(x3) + x4_avg + x5 + x6 + x7 + x8 + x9 + x10 + C(provinsi_id) + C(tahun)'
model = smf.ols(formula, data=train).fit(cov_type='cluster', cov_kwds={'groups': train['provinsi_id']})
print(model.summary())
```

### Kelebihan & Kekurangan

| ✅ Kelebihan | ❌ Kekurangan |
|-------------|--------------|
| Koefisien interpretabel langsung | Hanya 155 observasi |
| Menangkap fixed effects provinsi | Tidak bisa prediksi bulan tertentu |
| Menghilangkan pseudo-replication | Kehilangan variasi bulanan twp90 |
| Diakui valid secara econometric | Asumsi linearitas |
| Bisa uji VIF, Hausman, dll. | Perlu asumsi exogeneity |

---

## 🅱️ PIPELINE B — Monthly-Only XGBoost (Clean Baseline)

> **Filosofi**: Hanya gunakan fitur yang benar-benar bulanan. Lebih sedikit fitur, lebih jujur.  
> **Kompleksitas**: Rendah | **Prioritas**: KETIGA

### Arsitektur

```
model_panel.csv
    │
    ▼ [B.1 Feature Selection: Monthly Only]
Fitur bulanan: twp90_lag1, twp90_lag2, twp90_lag3, x1_bi_rate, x2_inflasi
Fitur annual sbg proxy: x3, x5, x6, x7, x8, x9, x10 (forward-carried, TIDAK diinterpolasi)
Panel identity: provinsi_id, bulan_sin, bulan_cos, time_trend
    │
    ▼ [B.2 Autoregressive Component]
Tambah lagged target: twp90_lag_1, twp90_lag_3, twp90_lag_6, twp90_lag_12
    │
    ▼ [B.3 Split: Time-based per provinsi]
Train: Jan 2022 – Des 2024 | Test: Jan 2025 – Des 2025
    │
    ▼ [B.4 Model: XGBoost + Panel Features]
XGBRegressor dengan provinsi_id as categorical feature
    │
    ▼ [B.5 Evaluasi multi-level]
Aggregate RMSE + per-province RMSE + vs naive baseline
```

### Feature Set Baru

```python
# B.2 — Autoregressive lags pada target (paling penting!)
for lag in [1, 2, 3, 6, 12]:
    df[f'twp90_lag_{lag}'] = df.groupby('provinsi_id')['twp90_pct'].shift(lag)

# Monthly features (murni bulanan)
monthly_features = [
    'x1_bi_rate_pct',        # ✅ benar-benar bulanan
    'x2_inflasi_yoy',        # ✅ benar-benar bulanan
    'x1_bi_rate_pct_lag_3',  # dengan lag 3 bulan
    'x2_inflasi_yoy_lag_3',
]

# Annual proxy features (step function, TIDAK diinterpolasi)
annual_proxy = ['x3_pdrb_per_kapita', 'x5_penetrasi_internet_pct',
                'x6_tabungan_miliar', 'x7_jumlah_kc_bank',
                'x8_ldr_pct', 'x9_npl_ratio', 'x10_rasio_umkm']

# Autoregressive features (sangat penting untuk time series)
ar_features = [f'twp90_lag_{lag}' for lag in [1, 2, 3, 6, 12]]

# Panel/time identity
identity = ['provinsi_id', 'bulan_sin', 'bulan_cos', 'time_trend']

X_cols = monthly_features + annual_proxy + ar_features + identity
```

### Kelebihan & Kekurangan

| ✅ Kelebihan | ❌ Kekurangan |
|-------------|--------------|
| Autoregressive component menangkap momentum | Annual proxy masih forward-carried |
| Provinsi ID menangkap cross-sectional FE | Tidak separasi kausal ekonomi makro |
| Tidak ada data leakage | R² mungkin tinggi karena AR, bukan fitur ekonomi |
| Bisa deploy untuk prediksi real-time | Perlu data twp90 bulan sebelumnya |

---

## 🅲 PIPELINE C — MIDAS Mixed-Frequency (Advanced)

> **Filosofi**: Gabungkan sinyal bulanan dan tahunan secara metodologis benar menggunakan weighting scheme.  
> **Kompleksitas**: Tinggi | **Prioritas**: KEEMPAT

### Arsitektur

```
model_panel.csv
    │
    ▼ [C.1 Separate frekuensi]
High-freq (monthly): twp90, bi_rate, inflasi
Low-freq (annual): pdrb, tpt, internet, x6–x10
    │
    ▼ [C.2 MIDAS weighting]
Annual features di-weight dengan Almon/Beta polynomial
sehingga tiap bulan dalam setahun mendapat bobot berbeda
    │
    ▼ [C.3 Mixed-Frequency Panel Model]
twp90_t = β₀ + Σ β_monthly(L)·x_monthly_t + Σ MIDAS(L^12)·x_annual_year(t) + ε
    │
    ▼ [C.4 Evaluasi]
Bandingkan vs Pipeline A dan B
```

### Catatan Implementasi

```python
# Paket Python untuk MIDAS regression
# pip install midaspy  atau gunakan manual polynomial weighting

# Alternatif sederhana: MIDAS approximation dengan interaksi waktu
# Annual proxy * (bulan/12) sebagai smooth time weight

df['pdrb_monthly_weight'] = df['x3_pdrb_per_kapita'] * (df['bulan'] / 12)
```

> **Note**: Pipeline C membutuhkan library khusus atau implementasi manual. Akan dieksekusi setelah A dan B memberikan baseline yang clear.

---

## 🅳 PIPELINE D — Two-Stage Komposit (Best of Both)

> **Filosofi**: Stage 1 memprediksi "level" TWP90 dari fitur ekonomi struktural; Stage 2 memprediksi "perubahan" dari fitur bulanan.  
> **Kompleksitas**: Tinggi | **Prioritas**: KELIMA

### Arsitektur

```
Stage 1: Annual Panel FE Regression
    Input: Annual cross-section features (x3–x10)
    Output: twp90_structural_pred (baseline level per provinsi-tahun)
    
Stage 2: Monthly Residual Model
    Input: (twp90_actual - twp90_structural_pred) + monthly features
    Output: twp90_residual_pred
    
Final: twp90_pred = twp90_structural_pred + twp90_residual_pred
```

### Kelebihan

- Memisahkan variasi **antar-provinsi** (struktural) dari variasi **dalam-provinsi** (temporal)
- Interpretasi lebih kaya: "Banten secara struktural punya TWP90 X, lalu bulan ini inflasi mendorongnya naik Y"
- Menghindari polusi signal antar frekuensi

---

## 📋 Rencana Eksekusi Bertahap

```
ITERASI 1: Track 0 — Fix Pipeline Existing
    ├── Fix PCHIP → step function
    ├── Fix TPT imputation → linear interpolation
    ├── Tambah fitur waktu & provinsi
    └── Tambah baseline comparison + train metrics
    EVALUASI: R², RMSE vs naive, train-test gap
    ─────────────────────────────────────────────
    
ITERASI 2: Pipeline A — Annual Panel Regression  
    ├── Agregasi tahunan
    ├── OLS Fixed Effects dengan clustered SE
    └── Uji VIF, Hausman test
    EVALUASI: Koefisien signifikansi, R², prediksi 2024–2025
    ─────────────────────────────────────────────

ITERASI 3: Pipeline B — Monthly-Only XGBoost
    ├── Feature selection: monthly + AR + annual proxy
    ├── XGBoost dengan provinsi_id
    └── Per-province evaluation
    EVALUASI: RMSE aggregate + per-province + vs naive
    ─────────────────────────────────────────────

ITERASI 4: Pipeline C — MIDAS (opsional)
    Tergantung hasil iterasi 1–3
    ─────────────────────────────────────────────

ITERASI 5: Pipeline D — Two-Stage Komposit
    Tergantung hasil iterasi 1–3
```

---

## 📐 Matriks Keputusan Pipeline

| Kriteria | Fix Existing | Pipeline A | Pipeline B | Pipeline C | Pipeline D |
|----------|:-----------:|:---------:|:---------:|:---------:|:---------:|
| Menangani granularity mismatch | ⚠️ Partial | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| Interpretasi kausal | ❌ No | ✅ Yes | ❌ No | ⚠️ Partial | ✅ Yes |
| Prediksi bulanan | ✅ Yes | ❌ No | ✅ Yes | ✅ Yes | ✅ Yes |
| Deployable real-time | ✅ Yes | ❌ No | ✅ Yes | ✅ Yes | ✅ Yes |
| Kompleksitas implementasi | 🟢 Low | 🟢 Low | 🟡 Medium | 🔴 High | 🔴 High |
| Observasi cukup | ✅ 1302 | ⚠️ 155 | ✅ ~1100 | ✅ 1302 | ✅ 1302 |
| Policy interpretability | ❌ Low | ✅ High | ⚠️ Medium | ⚠️ Medium | ✅ High |

---

## 🎯 Metrik Evaluasi Universal (semua pipeline)

Setiap iterasi akan dievaluasi menggunakan standar yang sama:

```
1. RMSE & MAE (aggregate)
2. RMSE per provinsi (breakdown)
3. R² (proportion of variance explained)
4. Naive baseline comparison:
   - Naive 1: y_pred = y_{t-1} (random walk)
   - Naive 2: y_pred = mean(y_train per provinsi)
5. Train vs Test RMSE gap (< 30% = healthy)
6. Residual autocorrelation (Ljung-Box test)
7. Heteroscedasticity check (Breusch-Pagan)
```

> **Go/No-Go criterion**: Model harus **mengalahkan Naive 1** (random walk) pada RMSE test untuk dianggap menambah nilai. R² sendiri tidak cukup.

---

## 📁 Struktur File Pipeline Baru

```
DatathonMETC/
├── model_panel.csv                     # Source data
├── 1_data_gathering/                   # Tidak berubah
├── 2_data_preprocessing/
│   ├── 2.1_data_cleaning_smoothing.ipynb    # ← DIPERBAIKI (Fix 1 & 2)
│   ├── 2.2_data_feature_engineering_lag.ipynb  # ← DIPERBAIKI (Fix 3)
│   └── output/
├── 3_modelling/
│   ├── 3.1_model_training_evaluation.ipynb  # ← DIPERBAIKI (Fix 4 & 5)
│   ├── 3.2_model_refinement.ipynb
│   └── output/
├── 4_visualization/
│   └── 4_eda_and_results_vis.ipynb
│
├── pipeline_A/                         # ← BARU
│   ├── A1_annual_aggregation.ipynb
│   ├── A2_panel_fixed_effects.ipynb
│   └── output/
│
├── pipeline_B/                         # ← BARU
│   ├── B1_feature_engineering_monthly.ipynb
│   ├── B2_xgboost_panel_aware.ipynb
│   └── output/
│
├── pipeline_C/                         # ← BARU (opsional)
│   └── ...
└── pipeline_D/                         # ← BARU (opsional)
    └── ...
```
