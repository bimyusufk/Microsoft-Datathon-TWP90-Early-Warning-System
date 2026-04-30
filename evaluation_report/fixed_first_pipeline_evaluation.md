# 📋 Evaluasi Fixed Pipeline (Iterasi 1) — Laporan Lengkap

> **Scope:** Pipeline arsitektur pertama setelah perbaikan (2.1 → 2.2 → 3.1 → 4)  
> **Model:** XGBoost Regressor | **Target:** twp90_pct (bulanan)  
> **Test Set:** Seluruh tahun 2025 (12 bulan × 31 provinsi = 372 observasi)

---

## 1. Ringkasan Metrik

| Model | RMSE | MAE | R² |
|-------|------|-----|-----|
| **XGBoost (Train)** | 0.0022 | 0.0015 | **0.954** |
| **XGBoost (Test)** | 0.0062 | 0.0028 | **0.666** |
| **Naive (Random Walk)** | 0.0049 | 0.0020 | **0.792** |

### 🔴 TEMUAN KRITIS #1: Model Kalah dari Naive Baseline

| Metrik | Model | Naive | Selisih |
|--------|-------|-------|---------|
| RMSE | 0.0062 | 0.0049 | Model **27% lebih buruk** |
| MAE | 0.0028 | 0.0020 | Model **40% lebih buruk** |
| R² | 0.666 | 0.792 | Naive menjelaskan **lebih banyak variasi** |

> [!CAUTION]
> **Model gagal memenuhi Go/No-Go criterion.** Prediksi sederhana "TWP90 bulan depan = TWP90 bulan ini" secara konsisten lebih akurat daripada XGBoost dengan 30+ fitur. Ini berarti model XGBoost **menambahkan noise, bukan signal**.

### 🔴 TEMUAN KRITIS #2: Overfitting Parah

- **Train RMSE:** 0.0022 | **Test RMSE:** 0.0062
- **Gap:** 64.3% — **jauh di atas threshold 30%**
- **Train R²:** 0.954 vs **Test R²:** 0.666
- Model menghafal pola training tetapi gagal generalize ke 2025

---

## 2. Analisis Per-Province

### Provinsi yang Mengalahkan Naive (8/31 = 25.8%)

| Provinsi | RMSE Model | RMSE Naive | Status |
|----------|-----------|-----------|--------|
| DI Yogyakarta | 0.00567 | 0.00571 | ✅ Marginal |
| Aceh | 0.00376 | 0.00406 | ✅ |
| Banten | 0.00319 | 0.00348 | ✅ |
| Jawa Tengah | 0.00296 | 0.00308 | ✅ Marginal |
| Kalimantan Tengah | 0.00259 | 0.00309 | ✅ |
| Jambi | 0.00193 | 0.00205 | ✅ Marginal |
| Kep. Bangka Belitung | 0.00167 | 0.00178 | ✅ Marginal |
| Sulawesi Barat | 0.00132 | 0.00222 | ✅ |

### Provinsi Terburuk (Model >> Naive)

| Provinsi | RMSE Model | RMSE Naive | Rasio |
|----------|-----------|-----------|-------|
| **DKI Jakarta** | **0.02981** | 0.02312 | **1.29×** |
| Jawa Timur | 0.00747 | 0.00483 | 1.55× |
| Sulawesi Tenggara | 0.00520 | 0.00076 | **6.84×** |

![Per-Province RMSE: Model vs Naive Baseline](C:\Users\bimyu\.gemini\antigravity\brain\e999456f-d4d1-4332-96ab-44a2023b4538\artifacts\per_province_rmse.png)

> [!WARNING]
> **DKI Jakarta (ID=2) mendominasi aggregate error.** RMSE-nya 0.030 — **5× lebih besar** dari rata-rata provinsi lain (~0.003). Ini karena TWP90 DKI Jakarta melonjak ke 0.1156-0.1158 di Nov-Des 2025 (dari baseline ~0.03), sementara model hanya memprediksi maksimal 0.052. Ini adalah **structural break/regime change** yang tidak tertangkap oleh model.

---

## 3. Analisis Grafik Visualisasi

### 3.1 Prediction vs Actual (6 Provinsi)

![Prediction vs Actual — 6 Provinces](C:\Users\bimyu\.gemini\antigravity\brain\e999456f-d4d1-4332-96ab-44a2023b4538\artifacts\pred_vs_actual_multi.png)

**Temuan:**

| Provinsi | Pola | Assessment |
|----------|------|------------|
| **Banten** | Prediksi menangkap arah tren, tapi amplitudo terlalu kecil | ⚠️ Underestimates peaks |
| **DKI Jakarta** | Prediksi datar di ~0.03 sementara actual melonjak ke 0.12 di akhir tahun | 🔴 Total failure — regime change |
| **Jawa Barat** | Prediksi datar, aktual turun lalu naik | ⚠️ Tidak menangkap variasi |
| **Jawa Tengah** | Prediksi kasar tapi arah mirip | ✅ Moderate |
| **DI Yogyakarta** | Prediksi gagal menangkap spike di Q2 | ⚠️ Missing dynamic |
| **Jawa Timur** | Prediksi datar, aktual naik tajam akhir tahun | 🔴 Significant miss |

**Pola umum:** Model memprediksi **terlalu flat/konservatif** — cenderung ke mean regression. Prediksi tidak menangkap pergerakan tajam (baik naik maupun turun).

### 3.2 Residual Diagnostics

![Residual Diagnostics](C:\Users\bimyu\.gemini\antigravity\brain\e999456f-d4d1-4332-96ab-44a2023b4538\artifacts\residual_diagnostics.png)

**Panel 1 — Residual Distribution:**
- Mayoritas residual terkonsentrasi di sekitar 0 ✅
- **Tapi**: terdapat ekor kiri yang berat (heavy left tail) hingga -0.08
- Ini menunjukkan model secara sistematis **under-predict** untuk observasi dengan TWP90 tinggi
- Distribusi **tidak normal** — skewed ke kiri

**Panel 2 — Residual vs Predicted:**
- Terdapat pola "fan-out" (heteroscedasticity): **semakin tinggi predicted value, semakin besar error variance**
- Di predicted ~0.01–0.02: error terkontrol ±0.005
- Di predicted ~0.03–0.05: error membengkak hingga ±0.08
- Ada beberapa outlier berat di bawah (residual -0.06 sampai -0.08)

**Panel 3 — Actual vs Predicted:**
- Titik-titik mengelompok di area 0.01–0.04 dengan fit yang lumayan
- **Tapi**: titik-titik dengan actual > 0.05 tidak diimbangi oleh predicted → predicted tertinggi hanya ~0.05
- Model memiliki **ceiling effect** — tidak bisa memprediksi TWP90 > 0.05

> [!WARNING]
> **Heteroscedasticity + ceiling effect** menunjukkan bahwa model **belajar mean, bukan variance**. Untuk provinsi/bulan dengan TWP90 tinggi (>0.04), model ini unreliable.

### 3.3 TWP90 Distribution

![Distribution of TWP90](C:\Users\bimyu\.gemini\antigravity\brain\e999456f-d4d1-4332-96ab-44a2023b4538\artifacts\twp90_distribution.png)

- **Median:** 0.0191 (1.91%)
- Distribusi **right-skewed** — mayoritas observasi di 0.005–0.030
- Ada **ekor kanan yang panjang** (long right tail) hingga ~0.12
- Outlier di ekor ini (terutama DKI Jakarta) mendistorsi evaluasi aggregat

**Implikasi:** Karena distribusi skewed, RMSE terlalu dipengaruhi oleh outlier. MAE atau MAPE mungkin lebih informatif untuk evaluasi.

### 3.4 Correlation Heatmap (Core Features)

![Correlation Heatmap](C:\Users\bimyu\.gemini\antigravity\brain\e999456f-d4d1-4332-96ab-44a2023b4538\artifacts\correlation_heatmap.png)

**Temuan utama:**

| Korelasi | Nilai | Interpretasi |
|----------|-------|-------------|
| twp90 ↔ x5_internet | **+0.26** | Korelasi **tertinggi** dengan target — tapi positif! Semakin tinggi internet penetration, semakin tinggi TWP90. Ini counterintuitive — kemungkinan confounded oleh urbanisasi/Jawa. |
| twp90 ↔ x10_umkm | **-0.22** | Negatif — rasio UMKM tinggi dikaitkan dengan TWP90 rendah. Bisa jadi efek provinsi kecil/pedesaan. |
| twp90 ↔ x8_ldr | **-0.15** | LDR tinggi → TWP90 rendah. Logis: bank yang aktif menyalurkan kredit = ekonomi lebih sehat. |
| twp90 ↔ x4_tpt | **+0.16** | Pengangguran tinggi → TWP90 tinggi. Logis secara ekonomi. |
| twp90 ↔ x1_bi_rate | **-0.08** | Hampir nol. BI rate (nasional) tidak memiliki korelasi cross-sectional yang kuat karena identik untuk semua provinsi. |
| twp90 ↔ x2_inflasi | **-0.07** | Hampir nol. Inflasi YoY memiliki asosiasi sangat lemah dengan TWP90. |
| x8_ldr ↔ x5_internet | **-0.46** | Cukup tinggi — multicollinearity potensi. Provinsi dengan internet tinggi cenderung LDR rendah. |
| x4_tpt ↔ x8_ldr | **-0.37** | Provinsi dengan pengangguran tinggi cenderung LDR rendah. |

> [!IMPORTANT]
> **Semua korelasi linear antara fitur independen dan twp90 sangat lemah** (< 0.30). Ini menjelaskan mengapa model kesulitan: sinyal ekonomi di data ini sangat noisy dan hubungan non-linear.

---

## 4. Analisis Feature Importance

| Rank | Feature | Importance | Tipe |
|------|---------|-----------|------|
| 1 | **twp90_lag_1** | 35.4% | AR (target bulan lalu) |
| 2 | x8_ldr_pct | 16.7% | Annual proxy |
| 3 | **twp90_lag_2** | 14.9% | AR |
| 4 | **twp90_lag_3** | 7.1% | AR |
| 5 | log_pdrb | 3.0% | Annual proxy (log) |

**Temuan:**
- **Top 3 fitur = autoregressive lags pada target** (57.4% total importance)
- Model pada dasarnya adalah **AR(3) model** dengan sedikit kontribusi dari fitur ekonomi
- Fitur makroekonomi (BI rate, inflasi) hampir **tidak relevan** (< 1.2% importance masing-masing)
- `x8_ldr_pct` (16.7%) adalah satu-satunya fitur ekonomi yang signifikan — tapi ini data tahunan (konstan per tahun)

> [!WARNING]
> **Paradoks:** Jika model sangat bergantung pada lag target (twp90 bulan lalu), lalu mengapa kalah dari naive baseline yang juga menggunakan twp90 bulan lalu? Karena model **over-adjusts** dari lag — menambahkan noise dari fitur lain, sementara naive hanya menggunakan lag-1 murni.

---

## 5. Root Cause Analysis

### Mengapa Model Kalah dari Naive?

```
Naive baseline: y_pred = y_{t-1}    ← simple, clean signal
XGBoost:        y_pred = f(y_{t-1}, y_{t-2}, ..., x1, x2, ..., x10)
                         ↑ bagus    ↑ noise   ↑ data tahunan = noise pada level bulanan
```

1. **Fitur tahunan (x3–x10) menambahkan noise** pada level bulanan. Nilainya konstan per tahun, tapi TWP90 berubah tiap bulan. Model mencoba belajar dari signal yang tidak ada.

2. **Overfitting pada training set**: R² train=0.954 vs test=0.666. Model menghafal idiosyncratic patterns di 2022–2024 yang tidak berlaku di 2025.

3. **DKI Jakarta regime change**: Lonjakan TWP90 DKI Jakarta ke 0.12 di akhir 2025 adalah event yang tidak ada preseden di training data (2022–2024 max ~0.05). Ini satu provinsi menyumbang ~24% total test error.

4. **Fitur ekonomi terlalu lemah**: Semua korelasi < 0.30 — tidak cukup kuat untuk memperbaiki prediksi AR murni.

---

## 6. Rekomendasi Tindak Lanjut

### Quick Wins (Bisa Diterapkan Segera)

1. **Evaluasi tanpa DKI Jakarta**: Hitung metrik aggregate tanpa provinsi outlier ini. Jika RMSE model tanpa DKI < naive, berarti model sebenarnya bekerja untuk 30 provinsi lain.

2. **Regularisasi lebih kuat**: Kurangi `max_depth` dari 5 → 3, naikkan `min_child_weight`, atau `alpha/lambda` regularization untuk mengurangi overfitting.

3. **Feature selection**: Coba model hanya dengan AR lags + `x8_ldr` + `provinsi_id` — buang fitur noise.

### Structural Improvements (Untuk Iterasi Berikutnya)

4. **Pisahkan model per-cluster provinsi**: DKI Jakarta memiliki dinamika sangat berbeda. Model terpisah untuk cluster Jawa/Non-Jawa mungkin lebih efektif.

5. **Tambah regime change detection**: Flag bulan-bulan dengan TWP90 > 2 std dari mean sebagai "alert mode".

6. **Pipeline A (Annual Panel OLS)** mungkin justru lebih cocok karena data sebagian besar tahunan. Evaluasi terpisah sudah dijadwalkan.

---

## 7. Verdict — Kualitas Fixed Pipeline

| Aspek | Score | Keterangan |
|-------|-------|------------|
| Data cleaning | ✅ 7/10 | PCHIP dihapus, TPT interpolasi linear — perbaikan solid |
| Feature engineering | ⚠️ 5/10 | AR lags bagus, tapi fitur tahunan masih noise pada level bulanan |
| Model performance | 🔴 3/10 | **Kalah dari naive baseline** — overfitting parah |
| Diagnostic completeness | ✅ 8/10 | Baseline, per-province, residual — semua tersedia |
| Policy readiness | 🔴 1/10 | Tidak bisa digunakan untuk kebijakan |

> [!CAUTION]
> **Kesimpulan akhir:** Perbaikan preprocessing berhasil menghilangkan data sintetis dan menambah transparansi. Namun model XGBoost bulanan tetap **gagal secara fundamental** karena mayoritas fitur berskala tahunan. Data ini lebih cocok dimodelkan secara tahunan — yang merupakan justifikasi kuat untuk **Pipeline A (Annual Panel OLS)**.
