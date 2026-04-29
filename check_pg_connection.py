"""
Script untuk memeriksa koneksi ke PostgreSQL dan mengeksplorasi schema datathon.
"""

DB_URL = "postgresql://postgres:root@localhost:5432/datathon"

print("=" * 60)
print("  CHECK KONEKSI PostgreSQL - Datathon")
print("=" * 60)
print(f"  URL: {DB_URL}")
print()

# --- 1. Cek psycopg tersedia
try:
    import psycopg
    print("[OK] psycopg ter-import")
except ImportError:
    print("[FAIL] psycopg tidak ter-install. Coba: pip install psycopg[binary]")
    exit(1)

# --- 2. Koneksi
try:
    conn = psycopg.connect(DB_URL)
    print("[OK] Koneksi berhasil!")
except Exception as e:
    print(f"[FAIL] Koneksi gagal: {e}")
    print()
    print("Kemungkinan penyebab:")
    print("  - PostgreSQL service belum berjalan")
    print("  - Database 'datathon' belum dibuat")
    print("  - User/password salah (postgres/root)")
    print("  - Port 5432 tidak terbuka")
    exit(1)

cur = conn.cursor()

# --- 3. Versi PostgreSQL
cur.execute("SELECT version()")
version = cur.fetchone()[0]
print(f"\n[INFO] PostgreSQL Version:\n  {version}")

# --- 4. Cek schema datathon
cur.execute("SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'datathon'")
schema_exists = cur.fetchone()
if schema_exists:
    print("\n[OK] Schema 'datathon' DITEMUKAN")
else:
    print("\n[WARN] Schema 'datathon' TIDAK ditemukan - perlu dijalankan schema_datathon.sql dulu")

# --- 5. List semua tabel dalam schema datathon
print("\n--- TABEL dalam schema 'datathon' ---")
cur.execute("""
    SELECT table_name, table_type
    FROM information_schema.tables
    WHERE table_schema = 'datathon'
    ORDER BY table_type, table_name
""")
tables = cur.fetchall()

if not tables:
    print("  (kosong - belum ada tabel)")
else:
    for tname, ttype in tables:
        label = "VIEW" if ttype == "VIEW" else "TABLE"
        print(f"  [{label}] {tname}")

# --- 6. Row count per tabel
print("\n--- ROW COUNTS per tabel ---")
fact_dim_tables = [t[0] for t in tables if t[1] == "BASE TABLE"]
for tname in fact_dim_tables:
    try:
        cur.execute(f"SELECT COUNT(*) FROM datathon.{tname}")
        count = cur.fetchone()[0]
        status = "v" if count > 0 else "-"
        print(f"  [{status}] {tname:<40} : {count:>8,} rows")
    except Exception as e:
        print(f"  [!] {tname:<40} : ERROR - {e}")

# --- 7. Cek kolom tabel utama
key_tables = [
    "dim_provinsi",
    "dim_waktu",
    "fact_p2p_pinjaman_provinsi",
    "fact_bi_rate",
]
for tname in key_tables:
    if tname not in fact_dim_tables:
        continue
    print(f"\n--- Kolom tabel: datathon.{tname} ---")
    cur.execute("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema = 'datathon' AND table_name = %s
        ORDER BY ordinal_position
    """, (tname,))
    cols = cur.fetchall()
    for col_name, dtype, nullable, default in cols:
        null_flag = "NULL" if nullable == "YES" else "NOT NULL"
        print(f"  {col_name:<35} {dtype:<20} {null_flag}")

# --- 8. Cek views
views = [t[0] for t in tables if t[1] == "VIEW"]
if views:
    print(f"\n--- VIEWS (siap pakai untuk modelling) ---")
    for v in views:
        print(f"  {v}")

conn.close()
print("\n" + "=" * 60)
print("  Selesai!")
print("=" * 60)
