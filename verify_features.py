"""
Verifikasi ketersediaan data untuk 10 features + 1 target di database datathon.
"""
import psycopg

DB_URL = "postgresql://postgres:root@localhost:5432/datathon"
conn = psycopg.connect(DB_URL)
cur = conn.cursor()

checks = [
    ("f(x) twp90", """
        SELECT COUNT(*), COUNT(DISTINCT pp.provinsi_id),
               MIN(w.tanggal), MAX(w.tanggal)
        FROM datathon.fact_p2p_pinjaman_provinsi pp
        JOIN datathon.dim_waktu w USING (waktu_id)
        WHERE pp.twp90 IS NOT NULL
    """),
    ("x1 bi_rate_pct", """
        SELECT COUNT(*), 1,
               MIN(w.tanggal), MAX(w.tanggal)
        FROM datathon.fact_bi_rate br
        JOIN datathon.dim_waktu w USING (waktu_id)
    """),
    ("x2 inflasi_yoy", """
        SELECT COUNT(*), COUNT(DISTINCT provinsi_id),
               MIN(w.tanggal), MAX(w.tanggal)
        FROM datathon.fact_inflasi_provinsi inf
        JOIN datathon.dim_waktu w USING (waktu_id)
        WHERE inf.inflasi_yoy IS NOT NULL
    """),
    ("x3 pdrb_per_kapita", """
        SELECT COUNT(*), COUNT(DISTINCT provinsi_id),
               MIN(tahun), MAX(tahun)
        FROM datathon.fact_pdrb_per_kapita
        WHERE pdrb_per_kapita_rp IS NOT NULL
    """),
    ("x4 tpt_pct", """
        SELECT COUNT(*), COUNT(DISTINCT provinsi_id),
               MIN(tahun), MAX(tahun)
        FROM datathon.fact_tpt
        WHERE tpt_pct IS NOT NULL
    """),
    ("x5 penetrasi_internet", """
        SELECT COUNT(*), COUNT(DISTINCT provinsi_id),
               MIN(tahun), MAX(tahun)
        FROM datathon.fact_penetrasi_internet
        WHERE penetrasi_pct IS NOT NULL
    """),
    ("x6 tabungan (dpk_miliar)", """
        SELECT COUNT(*), COUNT(DISTINCT p.provinsi_id),
               MIN(f.tahun), MAX(f.tahun)
        FROM datathon.fact_perbankan f
        JOIN datathon.dim_pemda pm ON pm.pemda_id = f."ID_Pemda"
        JOIN datathon.dim_provinsi p ON p.provinsi_id = pm.provinsi_id
        WHERE f.dpk_miliar IS NOT NULL
    """),
    ("x7 jumlah_kc_bank", """
        SELECT COUNT(*), COUNT(DISTINCT p.provinsi_id),
               MIN(f.tahun), MAX(f.tahun)
        FROM datathon.fact_perbankan f
        JOIN datathon.dim_pemda pm ON pm.pemda_id = f."ID_Pemda"
        JOIN datathon.dim_provinsi p ON p.provinsi_id = pm.provinsi_id
        WHERE f.jml_kc_bank IS NOT NULL
    """),
    ("x8 ldr_pct", """
        SELECT COUNT(*), COUNT(DISTINCT p.provinsi_id),
               MIN(f.tahun), MAX(f.tahun)
        FROM datathon.fact_perbankan f
        JOIN datathon.dim_pemda pm ON pm.pemda_id = f."ID_Pemda"
        JOIN datathon.dim_provinsi p ON p.provinsi_id = pm.provinsi_id
        WHERE f.ldr_pct IS NOT NULL
    """),
    ("x9 npl_ratio", """
        SELECT COUNT(*), COUNT(DISTINCT p.provinsi_id),
               MIN(f.tahun), MAX(f.tahun)
        FROM datathon.fact_perbankan f
        JOIN datathon.dim_pemda pm ON pm.pemda_id = f."ID_Pemda"
        JOIN datathon.dim_provinsi p ON p.provinsi_id = pm.provinsi_id
        WHERE f.npl_ratio IS NOT NULL
    """),
    ("x10 rasio_umkm", """
        SELECT COUNT(*), COUNT(DISTINCT p.provinsi_id),
               MIN(f.tahun), MAX(f.tahun)
        FROM datathon.fact_perbankan f
        JOIN datathon.dim_pemda pm ON pm.pemda_id = f."ID_Pemda"
        JOIN datathon.dim_provinsi p ON p.provinsi_id = pm.provinsi_id
        WHERE f.rasio_umkm IS NOT NULL
    """),
]

print(f"{'Feature':<25} {'Rows':>8} {'N Prov':>7} {'Min':>12} {'Max':>12}")
print("-" * 68)
for label, sql in checks:
    cur.execute(sql)
    n, prov, mn, mx = cur.fetchone()
    print(f"{label:<25} {n:>8,} {prov:>7} {str(mn):>12} {str(mx):>12}")

# Cek dim_provinsi: provinsi aktif
print("\n--- Provinsi aktif ---")
cur.execute("SELECT COUNT(*) FROM datathon.dim_provinsi WHERE is_aktif = TRUE")
print(f"Aktif: {cur.fetchone()[0]}")

# Cek fact_perbankan join dim_pemda → ada mapping provinsi_id?
print("\n--- fact_perbankan: dim_pemda join coverage ---")
cur.execute("""
    SELECT COUNT(*) FROM datathon.fact_perbankan f
    JOIN datathon.dim_pemda pm ON pm.pemda_id = f."ID_Pemda"
    WHERE pm.provinsi_id IS NOT NULL
""")
print(f"Rows dengan provinsi_id mapped: {cur.fetchone()[0]}")
cur.execute("""
    SELECT COUNT(*) FROM datathon.fact_perbankan f
    JOIN datathon.dim_pemda pm ON pm.pemda_id = f."ID_Pemda"
    WHERE pm.provinsi_id IS NULL
""")
print(f"Rows tanpa provinsi_id (NULL): {cur.fetchone()[0]}")

# Cek distinct snapshot_label
print("\n--- fact_perbankan snapshots ---")
cur.execute("SELECT DISTINCT tahun, snapshot_label FROM datathon.fact_perbankan ORDER BY 1, 2")
for t, s in cur.fetchall():
    print(f"  {t} - {s}")

# Cek TWP90 rentang waktu detail
print("\n--- TWP90 bulanan detail ---")
cur.execute("""
    SELECT w.tahun, COUNT(DISTINCT w.bulan), COUNT(DISTINCT pp.provinsi_id)
    FROM datathon.fact_p2p_pinjaman_provinsi pp
    JOIN datathon.dim_waktu w USING (waktu_id)
    WHERE pp.twp90 IS NOT NULL
    GROUP BY w.tahun ORDER BY w.tahun
""")
print(f"  {'Tahun':<6} {'Bulan':>6} {'Prov':>6}")
for t, b, p in cur.fetchall():
    print(f"  {t:<6} {b:>6} {p:>6}")

conn.close()
