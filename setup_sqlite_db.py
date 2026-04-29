"""
Setup script untuk membuat SQLite database dengan schema Datathon.
Mengkonversi PostgreSQL schema ke SQLite syntax.
"""

import sqlite3
from pathlib import Path

DB_PATH = r"c:\Users\bimyu\Documents\Projects\DatathonMETC\datathon.db"

# Hapus database lama jika ada
db_file = Path(DB_PATH)
if db_file.exists():
    db_file.unlink()
    print(f"Deleted existing database: {DB_PATH}")

# Buat koneksi
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Enable foreign keys
cursor.execute("PRAGMA foreign_keys = ON")

print("Creating SQLite database schema...\n")

# =====================================================================
#  A. DIMENSI TABLES
# =====================================================================

# A.1 dim_provinsi
cursor.execute("""
CREATE TABLE dim_provinsi (
    provinsi_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    kode_bps         TEXT UNIQUE,
    nama_provinsi    TEXT NOT NULL UNIQUE,
    nama_provinsi_std TEXT NOT NULL,
    pulau            TEXT,
    is_aktif         INTEGER DEFAULT 1
)
""")
cursor.execute("CREATE INDEX idx_dim_prov_std ON dim_provinsi(nama_provinsi_std)")
print("✓ Created dim_provinsi")

# A.2 dim_waktu
cursor.execute("""
CREATE TABLE dim_waktu (
    waktu_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    tanggal       DATE NOT NULL UNIQUE,
    tahun         INTEGER NOT NULL,
    kuartal       INTEGER NOT NULL,
    bulan         INTEGER NOT NULL,
    nama_bulan_id TEXT NOT NULL,
    semester      INTEGER NOT NULL
)
""")
cursor.execute("CREATE INDEX idx_dim_waktu_tahun ON dim_waktu(tahun)")
cursor.execute("CREATE INDEX idx_dim_waktu_yq ON dim_waktu(tahun, kuartal)")
print("✓ Created dim_waktu")

# A.3 dim_pemda
cursor.execute("""
CREATE TABLE dim_pemda (
    pemda_id      INTEGER PRIMARY KEY,
    nama_pemda    TEXT NOT NULL,
    tipe_pemda    TEXT NOT NULL,
    provinsi_id   INTEGER REFERENCES dim_provinsi(provinsi_id)
)
""")
cursor.execute("CREATE INDEX idx_dim_pemda_prov ON dim_pemda(provinsi_id)")
cursor.execute("CREATE INDEX idx_dim_pemda_tipe ON dim_pemda(tipe_pemda)")
print("✓ Created dim_pemda")

# A.4 dim_sektor_produktif
cursor.execute("""
CREATE TABLE dim_sektor_produktif (
    sektor_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    nama_sektor   TEXT NOT NULL UNIQUE,
    kategori      TEXT
)
""")
print("✓ Created dim_sektor_produktif")

# A.5 dim_kualitas_pembiayaan
cursor.execute("""
CREATE TABLE dim_kualitas_pembiayaan (
    kualitas_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    nama_kualitas TEXT NOT NULL UNIQUE,
    parent_id     INTEGER REFERENCES dim_kualitas_pembiayaan(kualitas_id),
    level_hirarki INTEGER
)
""")
print("✓ Created dim_kualitas_pembiayaan")

# =====================================================================
#  B. FACT TABLES - INDIKATOR MAKRO NASIONAL
# =====================================================================

# B.1 fact_bi_rate
cursor.execute("""
CREATE TABLE fact_bi_rate (
    waktu_id    INTEGER PRIMARY KEY REFERENCES dim_waktu(waktu_id),
    bi_rate_pct REAL NOT NULL,
    source_sheet TEXT DEFAULT 'BI Rate',
    loaded_at   DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")
print("✓ Created fact_bi_rate")

# =====================================================================
#  C. FACT TABLES - INDIKATOR MAKRO PROVINSI
# =====================================================================

# C.1 fact_penetrasi_internet
cursor.execute("""
CREATE TABLE fact_penetrasi_internet (
    provinsi_id    INTEGER NOT NULL REFERENCES dim_provinsi(provinsi_id),
    tahun          INTEGER NOT NULL,
    penetrasi_pct  REAL,
    source_sheet   TEXT DEFAULT 'Tingkat Penetrasi Internet',
    loaded_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (provinsi_id, tahun)
)
""")
print("✓ Created fact_penetrasi_internet")

# C.2 fact_pdrb
cursor.execute("""
CREATE TABLE fact_pdrb (
    provinsi_id   INTEGER NOT NULL REFERENCES dim_provinsi(provinsi_id),
    tahun         INTEGER NOT NULL,
    pdrb_rp       REAL,
    source_sheet  TEXT DEFAULT 'PDRB',
    loaded_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (provinsi_id, tahun)
)
""")
print("✓ Created fact_pdrb")

# C.3 fact_pdrb_per_kapita
cursor.execute("""
CREATE TABLE fact_pdrb_per_kapita (
    provinsi_id        INTEGER NOT NULL REFERENCES dim_provinsi(provinsi_id),
    tahun              INTEGER NOT NULL,
    pdrb_per_kapita_rp REAL,
    source_sheet       TEXT DEFAULT 'PDRB Per Kapita',
    loaded_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (provinsi_id, tahun)
)
""")
print("✓ Created fact_pdrb_per_kapita")

# C.4 fact_tpt
cursor.execute("""
CREATE TABLE fact_tpt (
    provinsi_id    INTEGER NOT NULL REFERENCES dim_provinsi(provinsi_id),
    tahun          INTEGER NOT NULL,
    periode        TEXT NOT NULL,
    tpt_pct        REAL,
    source_sheet   TEXT DEFAULT 'Tingkat Pengangguran Terbuka',
    loaded_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (provinsi_id, tahun, periode)
)
""")
print("✓ Created fact_tpt")

# C.5 fact_inflasi_provinsi
cursor.execute("""
CREATE TABLE fact_inflasi_provinsi (
    provinsi_id    INTEGER NOT NULL REFERENCES dim_provinsi(provinsi_id),
    waktu_id       INTEGER NOT NULL REFERENCES dim_waktu(waktu_id),
    inflasi_yoy    REAL,
    source_sheet   TEXT DEFAULT 'Inflasi per Provinsi Tahunan (YoY)',
    loaded_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (provinsi_id, waktu_id)
)
""")
print("✓ Created fact_inflasi_provinsi")

# =====================================================================
#  D. FACT TABLES - P2P LENDING
# =====================================================================

# D.1 fact_p2p_pinjaman_provinsi
cursor.execute("""
CREATE TABLE fact_p2p_pinjaman_provinsi (
    provinsi_id            INTEGER NOT NULL REFERENCES dim_provinsi(provinsi_id),
    waktu_id               INTEGER NOT NULL REFERENCES dim_waktu(waktu_id),
    jml_rek_penerima       INTEGER,
    outstanding_miliar     REAL,
    twp90                  REAL,
    source_sheet           TEXT DEFAULT 'Tab 9 (TWP90)',
    loaded_at              DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (provinsi_id, waktu_id)
)
""")
cursor.execute("CREATE INDEX idx_p2p_prov_waktu ON fact_p2p_pinjaman_provinsi(waktu_id, provinsi_id)")
print("✓ Created fact_p2p_pinjaman_provinsi")

# D.2 fact_p2p_kualitas_pembiayaan
cursor.execute("""
CREATE TABLE fact_p2p_kualitas_pembiayaan (
    kualitas_id         INTEGER NOT NULL REFERENCES dim_kualitas_pembiayaan(kualitas_id),
    waktu_id            INTEGER NOT NULL REFERENCES dim_waktu(waktu_id),
    jml_rek_penerima    INTEGER,
    outstanding_miliar  REAL,
    source_sheet        TEXT DEFAULT 'Tab 10 (Kualitas Pembiayaan)',
    loaded_at           DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (kualitas_id, waktu_id)
)
""")
print("✓ Created fact_p2p_kualitas_pembiayaan")

# D.3 fact_p2p_dana_diberikan
cursor.execute("""
CREATE TABLE fact_p2p_dana_diberikan (
    provinsi_id        INTEGER NOT NULL REFERENCES dim_provinsi(provinsi_id),
    waktu_id           INTEGER NOT NULL REFERENCES dim_waktu(waktu_id),
    jml_rek_pemberi    INTEGER,
    dana_diberikan_miliar REAL,
    source_sheet       TEXT DEFAULT 'Tab 5 (Dana Diberikan berdasark)',
    loaded_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (provinsi_id, waktu_id)
)
""")
print("✓ Created fact_p2p_dana_diberikan")

# D.4 fact_p2p_penyaluran_sektor
cursor.execute("""
CREATE TABLE fact_p2p_penyaluran_sektor (
    sektor_id           INTEGER NOT NULL REFERENCES dim_sektor_produktif(sektor_id),
    waktu_id            INTEGER NOT NULL REFERENCES dim_waktu(waktu_id),
    penyaluran_miliar   REAL,
    source_sheet        TEXT DEFAULT 'Tab 7 (Penyaluran ke Sektor Pro)',
    loaded_at           DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (sektor_id, waktu_id)
)
""")
print("✓ Created fact_p2p_penyaluran_sektor")

# =====================================================================
#  E. FACT TABLES - FISKAL & PERBANKAN
# =====================================================================

# E.1 fact_realisasi_tkd
cursor.execute("""
CREATE TABLE fact_realisasi_tkd (
    pemda_id        INTEGER NOT NULL REFERENCES dim_pemda(pemda_id),
    tahun           INTEGER NOT NULL,
    status_data     TEXT NOT NULL,
    komponen_tkd    TEXT NOT NULL,
    nilai_rp        REAL,
    source_sheet    TEXT DEFAULT 'Realisasi TKD pertahun',
    loaded_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (pemda_id, tahun, status_data, komponen_tkd)
)
""")
cursor.execute("CREATE INDEX idx_tkd_tahun ON fact_realisasi_tkd(tahun)")
cursor.execute("CREATE INDEX idx_tkd_komponen ON fact_realisasi_tkd(komponen_tkd)")
print("✓ Created fact_realisasi_tkd")

# E.2 fact_perbankan
cursor.execute("""
CREATE TABLE fact_perbankan (
    provinsi_id        INTEGER NOT NULL REFERENCES dim_provinsi(provinsi_id),
    tahun              INTEGER NOT NULL,
    snapshot_label     TEXT NOT NULL,
    kredit_total_miliar REAL,
    dpk_miliar          REAL,
    ldr_pct             REAL,
    zona_ldr            TEXT,
    npl_miliar          REAL,
    npl_ratio           REAL,
    kredit_umkm_miliar  REAL,
    rasio_umkm          REAL,
    umkm_per_kc_miliar  REAL,
    jml_kc_bank         INTEGER,
    source_sheet        TEXT DEFAULT 'Perbankan',
    loaded_at           DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (provinsi_id, tahun, snapshot_label)
)
""")
print("✓ Created fact_perbankan")

# =====================================================================
#  F. STAGING TABLES
# =====================================================================

cursor.execute("""
CREATE TABLE stg_p2p_pinjaman_raw (
    provinsi        TEXT,
    bulan_tahun     TEXT,
    jml_rek_raw     TEXT,
    outstanding_raw TEXT,
    twp90_raw       TEXT,
    loaded_at       DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")
print("✓ Created stg_p2p_pinjaman_raw")

cursor.execute("""
CREATE TABLE stg_pdrb_raw (
    provinsi    TEXT,
    tahun_raw   TEXT,
    pdrb_raw    TEXT,
    loaded_at   DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")
print("✓ Created stg_pdrb_raw")

# =====================================================================
#  Commit & summary
# =====================================================================

conn.commit()

# Verifikasi
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print(f"\n✅ Database created successfully at: {DB_PATH}")
print(f"Total tables created: {len(tables)}")
print("\nTables:")
for table in sorted(tables):
    cursor.execute(f"PRAGMA table_info({table[0]})")
    cols = cursor.fetchall()
    print(f"  - {table[0]} ({len(cols)} columns)")

conn.close()
print("\n✓ Database setup complete!")
