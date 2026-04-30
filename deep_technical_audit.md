# 🔬 Deep Technical Audit — TWP90 Early Warning System Pipeline

> **Auditor:** Antigravity AI | **Tanggal:** 2026-04-30  
> **Dataset:** `model_panel.csv` — 1,920 baris × 16 kolom  
> **Struktur:** Panel data 32 provinsi × 60 bulan (Jan 2021 – Des 2025)

---

## 📌 Executive Summary

| Aspek | Status | Severity |
|-------|--------|----------|
| Data Structural Integrity | ⚠️ Mixed-granularity | HIGH |
| Data Leakage | 🔴 CRITICAL (future data) | CRITICAL |
| Preprocessing Rigor | ⚠️ Questionable imputation | HIGH |
| Model Validity | ⚠️ Low R² + no baseline | MEDIUM |
| Causal Interpretation | 🔴 Misleading risk | CRITICAL |
| Visualization | ⚠️ Cherry-picked | MEDIUM |

**Verdict: Model TIDAK layak untuk policy insight (NO)**

---

## 🧠 1. Data Understanding & Structural Integrity

### 1.1 Panel Structure

- **Balanced panel**: ✅ Setiap 32 provinsi memiliki 60 observasi bulanan (Jan 2021 – Des 2025)
- **provinsi_id 19** di-drop di tahap gathering (menjadi 31 provinsi × 60 = 1,860 baris)
- `tanggal` dalam format string di CSV, dikonversi ke datetime di notebook 2.1 ✅

### 1.2 Granularity Mismatch — 🔴 CRITICAL

| Variabel | Granularity Asli | Pola di Dataset | Masalah |
|----------|-----------------|-----------------|---------|
| `twp90_pct` | Bulanan | Berubah tiap bulan | ✅ OK |
| `x1_bi_rate_pct` | Bulanan (nasional) | Identik semua provinsi per bulan | ⚠️ Bukan cross-sectional |
| `x2_inflasi_yoy` | Bulanan per provinsi | Berubah tiap bulan per provinsi | ✅ OK |
| `x3_pdrb_per_kapita` | **TAHUNAN** | **1 nilai per tahun, diulang 12×** | 🔴 Pseudo-replication |
| `x4_tpt_pct` | **SEMESTERAN** | Hanya bulan 2 & 8 (320/1920 = 16.7%) | 🔴 ~83% missing |
| `x5_penetrasi_internet` | **TAHUNAN** | Missing seluruh 2021; 1 nilai per tahun | 🔴 Pseudo-replication |
| `x6–x10` | **TAHUNAN** | 1 nilai per tahun, diulang 12× | 🔴 Pseudo-replication |

> [!CAUTION]
> **Pseudo-replication masif**: 8 dari 10 fitur independen (x3–x10) adalah data tahunan yang di-broadcast ke 12 bulan. Ini secara artifisial menaikkan jumlah observasi dari ~155 (31 prov × 5 tahun) menjadi 1,860. Model melihat "variasi" yang sebenarnya tidak ada — **inflating statistical power secara misleading**.

### 1.3 Fitur Sparse

**`x4_tpt_pct` (TPT / Pengangguran):**
- Hanya tersedia di bulan **Februari dan Agustus** (Sakernas semester)
- 320 non-null dari 1,920 total (16.7% available)
- Di notebook 2.1: `ffill(limit=5)` + `bfill(limit=1)` → **mengisi gap 5 bulan ke depan dengan nilai konstan**
- **Verdict:** Imputasi ini mengasumsikan pengangguran statis selama 5 bulan — tidak justified secara ekonomi. Harus dimodelkan sebagai fitur semesteran atau di-drop

**`x5_penetrasi_internet_pct`:**
- Missing seluruh tahun 2021 (384 missing = 20%)
- Data tahunan, diulang 12× per tahun
- **Verdict:** Bisa dipertahankan tapi harus di-acknowledge sebagai annual proxy

### 1.4 Missing x6–x10

- Missing **hanya di provinsi_id=19** (yang di-drop) → setelah filtering, x6–x10 lengkap ✅

---

## ⚠️ 2. Data Leakage & Temporal Consistency

### 2.1 FUTURE DATA LEAKAGE — 🔴 CRITICAL

Dataset berisi data hingga **Desember 2025**. Mengingat audit dilakukan April 2026, data 2025 mungkin sudah tersedia. **NAMUN:**

- Fitur tahunan (x3 PDRB, x5–x10) untuk tahun 2025 menggunakan **nilai tahun penuh** yang baru tersedia setelah 2025 berakhir
- Model di-train dengan data 2022–2024, di-test dengan 2025
- Fitur tahun 2025 (PDRB 2025, LDR 2025, dll.) digunakan untuk memprediksi TWP90 bulan Januari–Desember 2025 — **padahal PDRB 2025 baru diketahui di awal 2026**

> [!WARNING]
> **Look-ahead bias pada fitur tahunan**: Model menggunakan fitur x3–x10 tahun 2025 (yang baru tersedia 2026) untuk "memprediksi" TWP90 di Januari 2025. Dalam skenario real-time, fitur ini belum tersedia.

### 2.2 Lag Features — Partially Correct

```python
# Dari notebook 2.2
df[f'{feature}_lag_{lag}'] = df.groupby('provinsi_id')[feature].shift(lag)
```

- `shift(lag)` dengan lag=3,6 → mengambil nilai **3 atau 6 bulan sebelumnya** ✅
- **Tapi**: karena x3–x10 adalah data tahunan diulang 12×, `shift(3)` pada x3 menghasilkan **nilai yang sama** (karena konstan dalam setahun) kecuali di boundary tahun
- Lag pada data konstan = **fitur yang hampir identik** → multicollinearity artifisial

### 2.3 Train/Test Split

```python
train_data = df_model[df_model['tahun'] <= 2024]
test_data = df_model[df_model['tahun'] == 2025]
```

- ✅ Time-based split (bukan random)
- ✅ Train chronologically before test
- ⚠️ Tapi karena data 2021 di-filter di step 2.1 (`tahun > 2021`), train hanya 2022–2024
- ⚠️ Dengan lag-6, baris efektif dimulai dari ~Juli 2022 → **training window hanya ~2.5 tahun**

### 2.4 Scaling

- **Tidak ada scaling yang dilakukan** di seluruh pipeline
- Untuk XGBoost: ini OK (tree-based model invariant terhadap scaling) ✅
- Tapi jika akan membandingkan dengan model linear → perlu scaling setelah split

---

## 🧹 3. Preprocessing Audit

### 3.1 Missing Value Strategy

| Variabel | Strategy | Assessment |
|----------|----------|------------|
| x4_tpt_pct | ffill(5) + bfill(1) per provinsi | 🔴 Mengasumsikan konstan 5 bulan — terlalu agresif |
| x5_internet | Tidak diimputasi eksplisit di 2.1; di 2.2 gunakan ffill+bfill+median | ⚠️ ffill dari tahun sebelumnya tanpa justifikasi |
| Residual (2.2) | `ffill().bfill()` per provinsi, lalu `fillna(median)` global | 🔴 Median imputation tanpa time-awareness |

> [!WARNING]
> **Notebook 2.2 line 63-65**: Residual missing values diisi dengan `ffill().bfill()` lalu `fillna(median())`. Ini berarti jika suatu provinsi tidak memiliki data sama sekali untuk satu fitur, nilainya diisi dengan **median seluruh provinsi** — pooling cross-section yang mengabaikan heterogeneity regional.

### 3.2 PCHIP Smoothing — Questionable

Notebook 2.1 menerapkan PCHIP interpolation pada variabel "sticky" (x3–x10):

```python
is_anchor = group[col] != group[col].shift(1)  # anchor = titik perubahan
series_with_nans = group[col].where(is_anchor, np.nan)
group[col] = series_with_nans.interpolate(method='pchip')
```

- **Ide**: mengubah data stepwise (konstan per tahun) menjadi kurva smooth
- **Masalah**: Ini **membuat data buatan** antara titik-titik tahunan
  - Data Januari = nilai aktual, data Februari–November = interpolasi
  - Menciptakan **ilusi variasi bulanan** yang tidak ada di data asli
  - Model bisa belajar dari pola interpolasi, bukan pola ekonomi nyata

### 3.3 Feature Engineering

**Lag Features (3 & 6 bulan):**
- Secara teknis benar menggunakan `shift()` per provinsi
- Secara ekonomi: lag 3–6 bulan pada BI rate dan inflasi masuk akal (transmission lag)
- **Tapi pada data tahunan yang di-smoothing**, lag hanya menggeser kurva PCHIP → bukan informasi baru

**Yang TIDAK dilakukan tapi seharusnya ada:**
- ❌ Tidak ada `log(PDRB)` — padahal PDRB memiliki skala jutaan, distribusi right-skewed
- ❌ Tidak ada differencing untuk stationarity check
- ❌ Tidak ada interaction terms (misal: BI_rate × inflasi)
- ❌ Tidak ada encoding provinsi (fixed effects)
- ❌ Tidak ada seasonal dummies (bulan)

---

## 🤖 4. Modelling Audit

### 4.1 Model Choice

| Aspek | Temuan | Assessment |
|-------|--------|------------|
| Model | XGBoost Regressor | ✅ Robust untuk data tabular |
| Panel awareness | ❌ Tidak ada provinsi encoding | 🔴 Model tidak tahu panel structure |
| Time awareness | ❌ Tidak ada fitur waktu (bulan, trend) | 🔴 Model buta terhadap seasonality |
| Hyperparameter tuning | Manual → early stopping di 3.2 | ⚠️ Tidak ada systematic search |

> [!IMPORTANT]
> Model XGBoost dilatih **tanpa informasi provinsi atau waktu** sebagai fitur. Ini berarti model memperlakukan semua observasi sebagai i.i.d. — mengabaikan bahwa:
> 1. TWP90 Banten berbeda struktural dari TWP90 Papua
> 2. Ada tren waktu dan seasonality yang sistematis

### 4.2 Evaluation Metrics

| Metric | Baseline (30 fitur) | Refined (15 fitur) |
|--------|---------------------|---------------------|
| RMSE | 0.0086 | 0.0082 |
| MAE | 0.0044 | 0.0046 |
| R² | 0.3704 | 0.4193 |

**Assessment:**
- **R² = 0.37–0.42** → Model hanya menjelaskan ~40% variasi TWP90
- **Tidak ada baseline comparison** (misal: naive forecast `y_t = y_{t-1}` atau simple mean)
- **Tidak ada MAPE** untuk konteks persentase
- **Tidak ada per-province breakdown** — aggregated R² bisa menyembunyikan performa buruk di provinsi tertentu

### 4.3 Overfitting Check

- Notebook **tidak menampilkan train metrics** — hanya test metrics
- Tidak ada train vs test error comparison
- XGBoost dengan 1200 trees dan early stopping → risiko overfitting berkurang tapi **tidak diverifikasi**
- ⚠️ R² test hanya 0.42 mengindikasikan **underfitting**, bukan overfitting

### 4.4 Feature Importance — Suspicious

Top 3 features dari model:
1. `x7_jumlah_kc_bank_lag_6` (40.4%)
2. `x6_tabungan_miliar` (21.9%)
3. `x3_pdrb_per_kapita` (16.2%)

> [!CAUTION]
> **78.5% importance terpusat pada 3 fitur yang semuanya tahunan dan merupakan proxy ukuran ekonomi provinsi**. Model pada dasarnya belajar: "provinsi besar (banyak bank, tabungan tinggi, PDRB tinggi) punya TWP90 berbeda dari provinsi kecil" — ini **cross-sectional level effect, bukan prediksi temporal**.

---

## 📉 5. Economic Interpretability & Causality Risk

### 5.1 Korelasi ≠ Kausalitas — 🔴 CRITICAL

Notebook visualisasi menampilkan "Domino Effect: NPL → TWP90" — **tapi:**
- NPL dan TWP90 keduanya merupakan indikator risiko kredit
- Korelasi bisa karena **common cause** (kondisi makroekonomi)
- Tidak ada kontrol confounder (misal: GDP shock, kebijakan moneter)
- **Menampilkan NPL shifted +6 bulan sebagai "leading indicator" tanpa Granger causality test**

### 5.2 Multicollinearity

Fitur-fitur berikut sangat berkorelasi:
- `x1_bi_rate_pct` vs `x1_bi_rate_pct_lag_3` vs `x1_bi_rate_pct_lag_6` (BI rate berubah gradual)
- `x6_tabungan` vs `x7_kc_bank` vs `x3_pdrb` (semua proxy ukuran ekonomi provinsi)
- Lag fitur tahunan ≈ fitur asli (karena konstan dalam tahun)

### 5.3 Omitted Variable Bias

Variabel penting yang tidak ada:
- **Jumlah platform P2P lending** per provinsi (TWP90 adalah metrik fintech)
- **Volume penyaluran P2P** (denominator dari TWP90)
- **Demografi** (usia, pendidikan)
- **Kebijakan regulasi OJK** per periode

---

## 📊 6. Visualization Audit

### 6.1 Temuan

| Visualisasi | Masalah |
|------------|---------|
| Domino Effect (NPL→TWP90) | 🔴 Cherry-picked: hanya provinsi 1 (Banten). Tidak ditunjukkan apakah pola berlaku untuk semua provinsi |
| Pred vs Actual | ⚠️ Hanya provinsi 1. Tidak ada aggregate view |
| Distribusi fitur | ❌ Tidak ada |
| Correlation heatmap | ❌ Tidak ada |
| Residual plot | ❌ Tidak ada |
| Time trend multi-provinsi | ❌ Tidak ada |

### 6.2 Misleading Elements

- Judul "Domino Effect" menyiratkan kausalitas tanpa bukti statistik
- Dual-axis plot bisa distorsi visual relationship
- Tidak ada confidence interval atau error band pada prediksi

---

## ⚠️ 7. Bias & Risk Diagnostics

### 7.1 Data Bias — MNAR

**`x4_tpt_pct` (TPT):**
- Data hanya tersedia Februari & Agustus → **Missing by design** (Sakernas schedule)
- Ini **MNAR (Missing Not At Random)** — missingness ditentukan oleh jadwal survei
- Forward-fill 5 bulan mengasumsikan stabilitas yang tidak valid saat shock ekonomi

### 7.2 Temporal Bias

- **Periode COVID (2021)**: Dataset dimulai dari 2021 (masih pandemi) tapi **tidak ada variabel kontrol COVID**
- Notebook 2.1 mem-filter `tahun > 2021` → menghapus data 2021 dari training
- **Tapi**: data 2022 awal masih terpengaruh COVID recovery — tidak ada treatment

### 7.3 Regional Bias

- **BI Rate identik untuk semua provinsi** → tidak membawa informasi cross-sectional
- Fitur dominan (x6 tabungan, x7 kc_bank) sangat bias ke **Jawa** (DKI Jakarta: 3.9T vs Maluku: 15B tabungan — perbedaan ~260×)
- Model kemungkinan belajar **cluster effect** berdasarkan skala ekonomi, bukan dinamika TWP90

### 7.4 Future Prediction Validity

Dataset mencakup data hingga Des 2025 (termasuk Nov–Des 2025 yang **mungkin belum terjadi** saat model dibuat). Ini menunjukkan kemungkinan:
- Data sintetis/proyeksi untuk bulan mendatang
- Atau audit dilakukan retroactively setelah 2025

---

## 📌 8. Output Wajib

### 8.1 Diagnosis per Tahap Pipeline

| Tahap | Status | Temuan Utama |
|-------|--------|-------------|
| 1. Data Gathering | ⚠️ | Data dimuat tanpa validasi granularity; removal provinsi 19 tanpa penjelasan |
| 2.1 Cleaning | 🔴 | PCHIP smoothing menciptakan data buatan; ffill TPT terlalu agresif |
| 2.2 Feature Eng | ⚠️ | Lag pada data konstan tidak informatif; tidak ada log transform/differencing |
| 3.1 Modelling | 🔴 | Tidak ada panel/time awareness; tidak ada baseline comparison |
| 3.2 Refinement | ⚠️ | Perbaikan marginal; feature importance didominasi proxy skala ekonomi |
| 4. Visualization | 🔴 | Cherry-picked; causal claim tanpa bukti; tidak ada diagnostic plots |

### 8.2 Critical Flaws (Top 5)

| # | Flaw | Severity | Impact |
|---|------|----------|--------|
| 1 | **Pseudo-replication**: Data tahunan diulang 12× menghasilkan 1,860 observasi dari ~155 titik data independen | 🔴 CRITICAL | Inflated statistical power; standard errors terlalu kecil; semua metrik over-optimistic |
| 2 | **Future data leakage**: Fitur tahunan 2025 digunakan untuk memprediksi bulan-bulan awal 2025 | 🔴 CRITICAL | Model tidak deployable untuk real-time prediction |
| 3 | **PCHIP smoothing menciptakan data sintetis**: Interpolasi antara titik tahunan membuat variasi bulanan yang tidak ada | 🔴 HIGH | Model belajar dari artefak interpolasi |
| 4 | **Tidak ada panel/time awareness**: XGBoost tanpa province ID atau time features | 🔴 HIGH | Model tidak menangkap heterogeneity regional atau seasonality |
| 5 | **Causal claim tanpa justifikasi**: "Domino Effect NPL→TWP90" tanpa Granger test atau IV regression | 🔴 HIGH | Risiko misleading policy recommendation |

### 8.3 Risiko Bias Interpretasi Kebijakan

1. **"Jumlah kantor cabang bank (lag 6 bulan) adalah prediktor terpenting TWP90"** — Ini bukan prediksi temporal; ini hanya proxy bahwa provinsi dengan lebih banyak bank memiliki TWP90 berbeda. **Menutup kantor bank TIDAK akan menurunkan TWP90.**

2. **"Penetrasi internet meningkatkan ketahanan ekonomi"** — Korelasi terbalik antara internet penetration dan TWP90 bisa disebabkan oleh confounders (urbanisasi, income). Tanpa kontrol, klaim ini misleading.

3. **"NPL adalah leading indicator TWP90"** — Mungkin benar, tapi harus divalidasi dengan Granger causality test per provinsi, bukan single visual.

### 8.4 Rekomendasi Teknis

#### Perbaikan Preprocessing

```
1. JANGAN broadcast data tahunan ke bulanan
   → Gunakan annual panel (31 prov × 5 tahun = 155 obs) ATAU
   → Hanya gunakan fitur yang benar-benar bulanan (twp90, bi_rate, inflasi)

2. Untuk x4_tpt_pct: gunakan interpolasi linear antara
   Februari dan Agustus, BUKAN ffill konstan

3. Hapus PCHIP smoothing — atau jika ingin smooth,
   gunakan moving average yang transparan

4. Tambahkan log(PDRB), log(tabungan) untuk normalisasi skala

5. Lakukan stationarity test (ADF) pada twp90 per provinsi
```

#### Model Alternatif

```
1. Panel Fixed Effects regression:
   twp90 ~ x1 + x2 + ... + province_FE + time_FE
   → Baseline interpretable yang menangkap heterogeneity

2. XGBoost dengan fitur tambahan:
   - provinsi_id (as category)
   - bulan (seasonality)
   - time trend (integer counter)
   - lagged twp90 (autoregressive component)

3. Panel VAR (Vector Autoregression):
   → Untuk menguji Granger causality NPL→TWP90

4. Mixed-frequency model (MIDAS):
   → Menangani campuran data bulanan & tahunan secara proper
```

#### Validasi Lebih Robust

```
1. Expanding window cross-validation (bukan single split)
2. Per-province RMSE/MAE breakdown
3. Naive baseline comparison (y_pred = y_{t-1})
4. Diebold-Mariano test vs baseline
5. Residual autocorrelation check (Durbin-Watson)
```

### 8.5 Apakah Model Layak untuk Policy Insight?

## ❌ NO

**Alasan:**

1. **Data foundation cacat**: Pseudo-replication membuat semua inferensi statistik tidak valid
2. **Future leakage**: Model tidak bisa digunakan untuk prediksi real-time
3. **R² = 0.42**: Model hanya menjelaskan 42% variasi — 58% unexplained
4. **Feature importance bias**: Top features hanya menangkap perbedaan skala ekonomi antar provinsi, bukan dynamics temporal
5. **Causal claims tanpa bukti**: Risiko tinggi menghasilkan policy recommendation yang salah arah
6. **Tidak ada uncertainty quantification**: Tidak ada confidence interval pada prediksi

> [!IMPORTANT]
> Model ini bisa digunakan sebagai **eksplorasi awal** untuk mengidentifikasi variabel yang potensial relevan. Namun untuk **policy recommendation**, diperlukan restrukturisasi fundamental: perbaikan granularity data, proper panel econometrics, dan rigorous causal inference.
