"""
Build Model Panel DataFrame dari PostgreSQL datathon.

Output: model_panel.csv (32 provinsi × 60 bulan = 1920 baris)
Strategi: LEFT JOIN data as-is, TANPA forward-fill. 
Data tahunan/semesteran akan NULL di bulan yang tidak punya data langsung.

Kolom output:
  provinsi_id, nama_provinsi, tanggal, tahun, bulan,
  twp90_pct (target),
  x1_bi_rate_pct, x2_inflasi_yoy, x3_pdrb_per_kapita,
  x4_tpt_pct, x5_penetrasi_internet_pct,
  x6_tabungan_miliar, x7_jumlah_kc_bank,
  x8_ldr_pct, x9_npl_ratio, x10_rasio_umkm
"""

import pandas as pd
import psycopg

DB_URL     = "postgresql://postgres:root@localhost:5432/datathon"
OUTPUT_CSV = r"c:\Users\bimyu\Documents\Projects\DatathonMETC\model_panel.csv"

conn = psycopg.connect(DB_URL)

# ─── 1. Master Index: 32 provinsi aktif × 60 bulan (Jan 2021 – Des 2025) ────

print("Building master index...")
master_sql = """
    SELECT p.provinsi_id, p.nama_provinsi,
           w.waktu_id, w.tanggal, w.tahun, w.bulan
    FROM datathon.dim_provinsi p
    CROSS JOIN datathon.dim_waktu w
    WHERE p.is_aktif = TRUE
      AND w.tanggal >= '2021-01-01' AND w.tanggal <= '2025-12-01'
    ORDER BY p.provinsi_id, w.tanggal
"""
df = pd.read_sql(master_sql, conn)
print(f"  Master index: {df.shape[0]:,} rows ({df['provinsi_id'].nunique()} prov × {df['waktu_id'].nunique()} bulan)")

# ─── 2. Target: twp90_pct (bulanan, per provinsi) ───────────────────────────

print("Joining target: twp90_pct...")
twp_sql = """
    SELECT provinsi_id, waktu_id, twp90 AS twp90_pct
    FROM datathon.fact_p2p_pinjaman_provinsi
    WHERE twp90 IS NOT NULL
"""
df_twp = pd.read_sql(twp_sql, conn)
df = df.merge(df_twp, on=["provinsi_id", "waktu_id"], how="left")

# ─── 3. x1: BI Rate (bulanan, nasional → broadcast) ─────────────────────────

print("Joining x1: bi_rate_pct...")
bi_sql = """
    SELECT waktu_id, bi_rate_pct AS x1_bi_rate_pct
    FROM datathon.fact_bi_rate
"""
df_bi = pd.read_sql(bi_sql, conn)
df = df.merge(df_bi, on="waktu_id", how="left")

# ─── 4. x2: Inflasi YoY (bulanan, per provinsi) ─────────────────────────────

print("Joining x2: inflasi_yoy...")
inf_sql = """
    SELECT provinsi_id, waktu_id, inflasi_yoy AS x2_inflasi_yoy
    FROM datathon.fact_inflasi_provinsi
"""
df_inf = pd.read_sql(inf_sql, conn)
df = df.merge(df_inf, on=["provinsi_id", "waktu_id"], how="left")

# ─── 5. x3: PDRB Per Kapita (tahunan → as-is, NULL bulan tanpa data) ────────

print("Joining x3: pdrb_per_kapita...")
pdrb_sql = """
    SELECT provinsi_id, tahun, pdrb_per_kapita_rp AS x3_pdrb_per_kapita
    FROM datathon.fact_pdrb_per_kapita
"""
df_pdrb = pd.read_sql(pdrb_sql, conn)
df = df.merge(df_pdrb, on=["provinsi_id", "tahun"], how="left")

# ─── 6. x4: TPT (semesteran → as-is) ────────────────────────────────────────

print("Joining x4: tpt_pct...")
tpt_sql = """
    SELECT provinsi_id, tahun, periode,
           tpt_pct AS x4_tpt_pct,
           CASE WHEN periode = 'Februari' THEN 2 
                WHEN periode = 'Agustus' THEN 8 
           END AS bulan
    FROM datathon.fact_tpt
    WHERE tpt_pct IS NOT NULL
"""
df_tpt = pd.read_sql(tpt_sql, conn)
df = df.merge(df_tpt[["provinsi_id", "tahun", "bulan", "x4_tpt_pct"]],
              on=["provinsi_id", "tahun", "bulan"], how="left")

# ─── 7. x5: Penetrasi Internet (tahunan → as-is) ────────────────────────────

print("Joining x5: penetrasi_internet_pct...")
inet_sql = """
    SELECT provinsi_id, tahun, penetrasi_pct AS x5_penetrasi_internet_pct
    FROM datathon.fact_penetrasi_internet
"""
df_inet = pd.read_sql(inet_sql, conn)
df = df.merge(df_inet, on=["provinsi_id", "tahun"], how="left")

# ─── 8. x6–x10: Perbankan (tahunan → as-is, join via dim_pemda) ─────────────

print("Joining x6–x10: perbankan features...")
# fact_perbankan uses ID_Pemda → dim_pemda → provinsi_id
pb_sql = """
    SELECT pm.provinsi_id, f.tahun,
           f.dpk_miliar             AS x6_tabungan_miliar,
           f.jml_kc_bank            AS x7_jumlah_kc_bank,
           f.ldr_pct                AS x8_ldr_pct,
           f.npl_ratio              AS x9_npl_ratio,
           f.rasio_umkm             AS x10_rasio_umkm
    FROM datathon.fact_perbankan f
    JOIN datathon.dim_pemda pm ON pm.pemda_id = f."ID_Pemda"
    WHERE pm.provinsi_id IS NOT NULL
"""
df_pb = pd.read_sql(pb_sql, conn)
df = df.merge(df_pb, on=["provinsi_id", "tahun"], how="left")

conn.close()

# ─── 9. Cleanup & output ─────────────────────────────────────────────────────

# Drop helper columns
df = df.drop(columns=["waktu_id"])

# Reorder columns
final_cols = [
    "provinsi_id", "nama_provinsi", "tanggal", "tahun", "bulan",
    "twp90_pct",
    "x1_bi_rate_pct", "x2_inflasi_yoy", "x3_pdrb_per_kapita",
    "x4_tpt_pct", "x5_penetrasi_internet_pct",
    "x6_tabungan_miliar", "x7_jumlah_kc_bank",
    "x8_ldr_pct", "x9_npl_ratio", "x10_rasio_umkm",
]
df = df[final_cols]

# Sort
df = df.sort_values(["provinsi_id", "tanggal"]).reset_index(drop=True)

# ─── 10. Summary ─────────────────────────────────────────────────────────────

print(f"\n{'='*60}")
print(f"  MODEL PANEL DATAFRAME — SUMMARY")
print(f"{'='*60}")
print(f"  Shape        : {df.shape}")
print(f"  Provinsi     : {df['provinsi_id'].nunique()}")
print(f"  Bulan        : {df['tanggal'].nunique()}")
print(f"  Rentang      : {df['tanggal'].min()} — {df['tanggal'].max()}")

print(f"\n  Missing values per kolom:")
missing = df.isnull().sum()
total = len(df)
for col in final_cols[5:]:
    pct = missing[col] / total * 100
    bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
    print(f"    {col:<30} {missing[col]:>6} / {total} ({pct:5.1f}%) {bar}")

print(f"\n  Describe (numeric features):")
print(df[final_cols[5:]].describe().round(4).to_string())

print(f"\n  First 5 rows:")
print(df.head().to_string())

# Save
df.to_csv(OUTPUT_CSV, index=False)
print(f"\n✅ Saved to: {OUTPUT_CSV}")
print(f"   Shape: {df.shape}")
