"""
ETL script: Sheet "Perbankan" dari XLSX → datathon.fact_perbankan (PostgreSQL)

Struktur sheet Perbankan:
  Row 1: Header grup (Identitas, Kredit DPK & NPL, UMKM, Bank Kantor)
  Row 2: Header kolom aktual
  Row 3+: Data (ID_Pemda, Provinsi, Tahun, Snapshot, 10 metrik)

Kolom target (fact_perbankan):
  pemda_id, tahun, snapshot_label, kredit_total_miliar, dpk_miliar, ldr_pct,
  zona_ldr, npl_miliar, npl_ratio, kredit_umkm_miliar, rasio_umkm, umkm_per_kc_miliar,
  jml_kc_bank, source_sheet, loaded_at
"""

import re
import psycopg
from openpyxl import load_workbook

# ─── Config ───────────────────────────────────────────────────────────────────
DB_URL    = "postgresql://postgres:root@localhost:5432/datathon"
XLSX_PATH = r"c:\Users\bimyu\Documents\Projects\DatathonMETC\data prep datathon dicoding.xlsx"
SHEET_NAME = "Perbankan"

# Indeks kolom (0-based), berdasarkan hasil eksplorasi:
COL_ID_PEMDA        = 0
COL_PROVINSI        = 1
COL_TAHUN           = 2
COL_SNAPSHOT        = 3
COL_KREDIT_TOTAL    = 4
COL_DPK             = 5
COL_LDR             = 6
COL_ZONA_LDR        = 7
COL_NPL_MILIAR      = 8
COL_NPL_RATIO       = 9
COL_KREDIT_UMKM     = 10
COL_RASIO_UMKM      = 11
COL_UMKM_PER_KC     = 12
COL_JML_KC          = 13

# ─── Helpers ──────────────────────────────────────────────────────────────────

def normalize_province_std(name: str | None) -> str | None:
    """Lowercase + strip prefix untuk join ke nama_provinsi_std di dim_provinsi."""
    if name is None:
        return None
    s = str(name).strip()
    s = re.sub(r"^(provinsi|kab\.|kabupaten|kota)\s+", "", s, flags=re.I)
    s = re.sub(r"\s+", " ", s)
    return s.lower()


def safe_float(val) -> float | None:
    if val is None or val == "":
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def safe_int(val) -> int | None:
    f = safe_float(val)
    return int(f) if f is not None else None


# ─── Baca XLSX ────────────────────────────────────────────────────────────────

print(f"Membaca sheet '{SHEET_NAME}' dari XLSX...")
wb = load_workbook(XLSX_PATH, data_only=True, read_only=True)
ws = wb[SHEET_NAME]
rows = list(ws.iter_rows(values_only=True))
wb.close()

# Skip 2 baris header, ambil baris data (row 3+)
data_rows = rows[2:]  # row index 2 = Excel row 3
print(f"Total baris (termasuk kosong): {len(data_rows)}")

# Filter baris valid: col 0 (ID_Pemda) tidak kosong
valid_rows = [
    r for r in data_rows
    if r and len(r) > COL_ID_PEMDA and r[COL_ID_PEMDA] not in (None, "")
]
print(f"Baris data valid: {len(valid_rows)}")

# ─── Koneksi ──────────────────────────────────────────────────────────────────

print("\nKoneksi ke PostgreSQL...")
conn = psycopg.connect(DB_URL)
cur = conn.cursor()

# ─── Parse & Upsert ───────────────────────────────────────────────────────────

upsert_sql = """
INSERT INTO datathon.fact_perbankan (
    pemda_id, tahun, snapshot_label,
    kredit_total_miliar, dpk_miliar, ldr_pct,
    zona_ldr, npl_miliar, npl_ratio,
    kredit_umkm_miliar, rasio_umkm, umkm_per_kc_miliar,
    jml_kc_bank, source_sheet
) VALUES (
    %s, %s, %s,
    %s, %s, %s,
    %s, %s, %s,
    %s, %s, %s,
    %s, %s
)
ON CONFLICT (pemda_id, tahun, snapshot_label) DO UPDATE SET
    kredit_total_miliar = EXCLUDED.kredit_total_miliar,
    dpk_miliar          = EXCLUDED.dpk_miliar,
    ldr_pct             = EXCLUDED.ldr_pct,
    zona_ldr            = EXCLUDED.zona_ldr,
    npl_miliar          = EXCLUDED.npl_miliar,
    npl_ratio           = EXCLUDED.npl_ratio,
    kredit_umkm_miliar  = EXCLUDED.kredit_umkm_miliar,
    rasio_umkm          = EXCLUDED.rasio_umkm,
    umkm_per_kc_miliar  = EXCLUDED.umkm_per_kc_miliar,
    jml_kc_bank         = EXCLUDED.jml_kc_bank,
    loaded_at           = CURRENT_TIMESTAMP
"""

inserted  = 0
skipped   = 0

print("\nMemproses dan memuat data...")

for row in valid_rows:
    pemda_id = str(row[COL_ID_PEMDA]).strip()
    
    tahun = safe_int(row[COL_TAHUN])
    if tahun is None:
        skipped += 1
        continue

    snapshot_label = str(row[COL_SNAPSHOT]).strip() if row[COL_SNAPSHOT] else None
    if snapshot_label is None:
        skipped += 1
        continue

    params = (
        pemda_id,
        tahun,
        snapshot_label,
        safe_float(row[COL_KREDIT_TOTAL]),
        safe_float(row[COL_DPK]),
        safe_float(row[COL_LDR]),
        str(row[COL_ZONA_LDR]).strip() if row[COL_ZONA_LDR] else None,
        safe_float(row[COL_NPL_MILIAR]),
        safe_float(row[COL_NPL_RATIO]),
        safe_float(row[COL_KREDIT_UMKM]),
        safe_float(row[COL_RASIO_UMKM]),
        safe_float(row[COL_UMKM_PER_KC]),
        safe_int(row[COL_JML_KC]),
        "Perbankan",
    )

    cur.execute(upsert_sql, params)
    inserted += 1

conn.commit()

# ─── Laporan ──────────────────────────────────────────────────────────────────

print(f"\n✅ Selesai!")
print(f"   Rows diproses / upserted : {inserted}")
print(f"   Rows di-skip             : {skipped}")

# ─── Validasi ──────────────────────────────────────────────────────────────────

print("\n--- Validasi: Row count per (tahun, snapshot) ---")
cur.execute("""
    SELECT tahun, snapshot_label, COUNT(*) AS n_pemda
    FROM datathon.fact_perbankan
    GROUP BY tahun, snapshot_label
    ORDER BY tahun, snapshot_label
""")
validation = cur.fetchall()
print(f"{'Tahun':<8} {'Snapshot':<12} {'N Pemda':>10}")
print("-" * 34)
for tahun, snap, n in validation:
    print(f"{tahun:<8} {snap:<12} {n:>10}")

print(f"\nTotal rows di fact_perbankan: ", end="")
cur.execute("SELECT COUNT(*) FROM datathon.fact_perbankan")
print(cur.fetchone()[0])

# Contoh data
print("\n--- Sample 5 rows ---")
cur.execute("""
    SELECT p.nama_provinsi, f.tahun, f.snapshot_label,
           f.kredit_total_miliar, f.dpk_miliar, f.ldr_pct, f.zona_ldr,
           f.npl_ratio, f.jml_kc_bank
    FROM datathon.fact_perbankan f
    JOIN datathon.dim_provinsi p USING (provinsi_id)
    ORDER BY f.tahun, p.nama_provinsi
    LIMIT 5
""")
print(f"{'Provinsi':<28} {'Tahun':<6} {'Snap':<8} {'Kredit':>12} {'DPK':>12} {'LDR':>8} {'Zona':<8} {'NPL%':>7} {'KC':>6}")
print("-" * 100)
for row in cur.fetchall():
    nama, thn, snap, kredit, dpk, ldr, zona, npl, kc = row
    print(f"{nama:<28} {thn:<6} {snap:<8} {kredit:>12.2f} {dpk:>12.2f} {ldr:>8.4f} {zona:<8} {npl:>7.4f} {kc:>6}")

conn.close()
