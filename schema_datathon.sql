-- =====================================================================
--  SKEMA DATABASE - DATATHON DICODING (Data Prep)
--  Tujuan : Memudahkan agregasi multi-sumber untuk modelling P2P Lending
--  Dialect: PostgreSQL 14+ (mudah disesuaikan ke MySQL/SQLite/BigQuery)
--  Penulis: Generated schema, 2026
-- =====================================================================
--  Filosofi desain:
--    1. STAR SCHEMA dengan dimensi terkonformasi (provinsi, waktu, pemda).
--    2. Semua fakta time-series di-NORMALISASI ke long format (tidy data),
--       bukan wide-format seperti di Excel sumber. Ini memudahkan JOIN,
--       agregasi (rollup tahunan, kuartalan), dan feature engineering.
--    3. Granularitas waktu disimpan sebagai DATE (selalu tanggal-1 bulan)
--       agar bisa di-aggregate ke berbagai level (bulan, kuartal, tahun).
--    4. Setiap fakta menyimpan kolom "source_sheet" untuk audit trail.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 0. SCHEMA & EKSTENSI
-- ---------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS datathon;
SET search_path TO datathon;


-- =====================================================================
--  A. TABEL DIMENSI (master / referensi)
-- =====================================================================

-- ---------------------------------------------------------------------
-- A.1  dim_provinsi
--      Master 38 provinsi Indonesia. Dipakai oleh hampir SEMUA fakta.
--      kode_bps berguna untuk join lintas dataset eksternal (BPS).
-- ---------------------------------------------------------------------
CREATE TABLE dim_provinsi (
    provinsi_id      SMALLSERIAL PRIMARY KEY,
    kode_bps         VARCHAR(2)  UNIQUE,                 -- '11','12',...
    nama_provinsi    VARCHAR(64) NOT NULL UNIQUE,        -- 'Aceh','Dki Jakarta',...
    nama_provinsi_std VARCHAR(64) NOT NULL,              -- versi lower/normalized untuk fuzzy join
    pulau            VARCHAR(32),                        -- Sumatera, Jawa, Kalimantan, dll
    is_aktif         BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_dim_prov_std ON dim_provinsi(nama_provinsi_std);


-- ---------------------------------------------------------------------
-- A.2  dim_waktu
--      Calendar table bulanan 2019-01 .. 2026-12.
--      Memudahkan rollup ke quarter / year tanpa fungsi date di query.
-- ---------------------------------------------------------------------
CREATE TABLE dim_waktu (
    waktu_id      SERIAL PRIMARY KEY,
    tanggal       DATE    NOT NULL UNIQUE,    -- selalu YYYY-MM-01
    tahun         SMALLINT NOT NULL,
    kuartal       SMALLINT NOT NULL,          -- 1..4
    bulan         SMALLINT NOT NULL,          -- 1..12
    nama_bulan_id VARCHAR(12) NOT NULL,       -- Januari, Februari,...
    semester      SMALLINT NOT NULL           -- 1..2
);

CREATE INDEX idx_dim_waktu_tahun ON dim_waktu(tahun);
CREATE INDEX idx_dim_waktu_yq    ON dim_waktu(tahun, kuartal);


-- ---------------------------------------------------------------------
-- A.3  dim_pemda
--      Pemda (provinsi/kab/kota) untuk sheet "Realisasi TKD pertahun"
--      yang granularitasnya kabupaten/kota, bukan provinsi.
-- ---------------------------------------------------------------------
CREATE TABLE dim_pemda (
    pemda_id      INTEGER PRIMARY KEY,        -- ID_Pemda dari sumber
    nama_pemda    VARCHAR(128) NOT NULL,      -- 'Kab. Aceh Barat'
    tipe_pemda    VARCHAR(16)  NOT NULL,      -- 'Provinsi' | 'Kabupaten' | 'Kota'
    provinsi_id   SMALLINT REFERENCES dim_provinsi(provinsi_id)
);

CREATE INDEX idx_dim_pemda_prov ON dim_pemda(provinsi_id);
CREATE INDEX idx_dim_pemda_tipe ON dim_pemda(tipe_pemda);


-- ---------------------------------------------------------------------
-- A.4  dim_sektor_produktif
--      Master sektor untuk Tab 7 (Penyaluran ke Sektor Produktif)
-- ---------------------------------------------------------------------
CREATE TABLE dim_sektor_produktif (
    sektor_id     SMALLSERIAL PRIMARY KEY,
    nama_sektor   VARCHAR(128) NOT NULL UNIQUE,
    kategori      VARCHAR(64)                 -- e.g. 'Primer','Sekunder','Tersier'
);


-- ---------------------------------------------------------------------
-- A.5  dim_kualitas_pembiayaan
--      Master kategori kualitas pembiayaan untuk Tab 10
--      (Total Outstanding, Perseorangan, Badan Usaha, Lancar, Macet, dll)
-- ---------------------------------------------------------------------
CREATE TABLE dim_kualitas_pembiayaan (
    kualitas_id   SMALLSERIAL PRIMARY KEY,
    nama_kualitas VARCHAR(128) NOT NULL UNIQUE,
    parent_id     SMALLINT REFERENCES dim_kualitas_pembiayaan(kualitas_id),
    level_hirarki SMALLINT                    -- 0=total, 1=segmen, 2=sub-segmen
);


-- =====================================================================
--  B. TABEL FAKTA - INDIKATOR MAKRO (Indonesia level)
-- =====================================================================

-- ---------------------------------------------------------------------
-- B.1  fact_bi_rate
--      Source: sheet 'BI Rate'. Granular: bulanan, nasional.
-- ---------------------------------------------------------------------
CREATE TABLE fact_bi_rate (
    waktu_id    INTEGER PRIMARY KEY REFERENCES dim_waktu(waktu_id),
    bi_rate_pct NUMERIC(6,4) NOT NULL,         -- contoh: 5.75 (%)
    source_sheet VARCHAR(64) DEFAULT 'BI Rate',
    loaded_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- =====================================================================
--  C. TABEL FAKTA - INDIKATOR MAKRO PROVINSI (tahunan)
-- =====================================================================

-- ---------------------------------------------------------------------
-- C.1  fact_penetrasi_internet
--      Source: 'Tingkat Penetrasi Internet'. Tahunan, per provinsi.
-- ---------------------------------------------------------------------
CREATE TABLE fact_penetrasi_internet (
    provinsi_id    SMALLINT NOT NULL REFERENCES dim_provinsi(provinsi_id),
    tahun          SMALLINT NOT NULL,
    penetrasi_pct  NUMERIC(6,4),               -- 0.7565 = 75.65%
    source_sheet   VARCHAR(64) DEFAULT 'Tingkat Penetrasi Internet',
    loaded_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (provinsi_id, tahun)
);


-- ---------------------------------------------------------------------
-- C.2  fact_pdrb
--      Source: 'PDRB'. Tahunan, per provinsi. Nilai absolut (Rupiah).
-- ---------------------------------------------------------------------
CREATE TABLE fact_pdrb (
    provinsi_id   SMALLINT NOT NULL REFERENCES dim_provinsi(provinsi_id),
    tahun         SMALLINT NOT NULL,
    pdrb_rp       NUMERIC(22,2),               -- nilai dalam Rupiah
    source_sheet  VARCHAR(64) DEFAULT 'PDRB',
    loaded_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (provinsi_id, tahun)
);


-- ---------------------------------------------------------------------
-- C.3  fact_pdrb_per_kapita
--      Source: 'PDRB Per Kapita'. Tahunan, per provinsi. Rupiah/kapita.
-- ---------------------------------------------------------------------
CREATE TABLE fact_pdrb_per_kapita (
    provinsi_id        SMALLINT NOT NULL REFERENCES dim_provinsi(provinsi_id),
    tahun              SMALLINT NOT NULL,
    pdrb_per_kapita_rp NUMERIC(18,2),
    source_sheet       VARCHAR(64) DEFAULT 'PDRB Per Kapita',
    loaded_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (provinsi_id, tahun)
);


-- ---------------------------------------------------------------------
-- C.4  fact_tpt (Tingkat Pengangguran Terbuka)
--      Source: 'Tingkat Pengangguran Terbuka'. Semesteran (Feb & Agt),
--      per provinsi. Disimpan dengan periode_label utk bedakan Feb/Agt.
-- ---------------------------------------------------------------------
CREATE TABLE fact_tpt (
    provinsi_id    SMALLINT NOT NULL REFERENCES dim_provinsi(provinsi_id),
    tahun          SMALLINT NOT NULL,
    periode        VARCHAR(8) NOT NULL,        -- 'Februari' | 'Agustus'
    tpt_pct        NUMERIC(6,4),               -- 5.75 (%) atau 0.0575 (rasio) -- standardisasi di ETL
    source_sheet   VARCHAR(64) DEFAULT 'Tingkat Pengangguran Terbuka',
    loaded_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (provinsi_id, tahun, periode)
);


-- ---------------------------------------------------------------------
-- C.5  fact_inflasi_provinsi
--      Source: 'Inflasi per Provinsi Tahunan (YoY)'.
--      Bulanan, per provinsi (Jan 2021 - Mar 2026). YoY %.
-- ---------------------------------------------------------------------
CREATE TABLE fact_inflasi_provinsi (
    provinsi_id    SMALLINT NOT NULL REFERENCES dim_provinsi(provinsi_id),
    waktu_id       INTEGER  NOT NULL REFERENCES dim_waktu(waktu_id),
    inflasi_yoy    NUMERIC(8,5),               -- bisa negatif (deflasi)
    source_sheet   VARCHAR(64) DEFAULT 'Inflasi per Provinsi Tahunan (YoY)',
    loaded_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (provinsi_id, waktu_id)
);


-- =====================================================================
--  D. TABEL FAKTA - P2P LENDING (CORE TABEL UNTUK MODELLING)
-- =====================================================================

-- ---------------------------------------------------------------------
-- D.1  fact_p2p_pinjaman_provinsi
--      Source: 'Tab 9 (TWP90)'. Bulanan, per provinsi.
--      3 metrik per cell: jumlah_rekening, outstanding, twp90.
--      Ini MAIN TABLE untuk target/feature modelling kredit P2P.
-- ---------------------------------------------------------------------
CREATE TABLE fact_p2p_pinjaman_provinsi (
    provinsi_id            SMALLINT NOT NULL REFERENCES dim_provinsi(provinsi_id),
    waktu_id               INTEGER  NOT NULL REFERENCES dim_waktu(waktu_id),
    jml_rek_penerima       BIGINT,             -- Jumlah Rekening Penerima Pinjaman Aktif (entitas)
    outstanding_miliar     NUMERIC(14,2),      -- Outstanding Pinjaman (miliar Rp)
    twp90                  NUMERIC(8,5),       -- TWP90 sebagai rasio (0.0274 = 2.74%)
    source_sheet           VARCHAR(64) DEFAULT 'Tab 9 (TWP90)',
    loaded_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (provinsi_id, waktu_id)
);

CREATE INDEX idx_p2p_prov_waktu ON fact_p2p_pinjaman_provinsi(waktu_id, provinsi_id);


-- ---------------------------------------------------------------------
-- D.2  fact_p2p_kualitas_pembiayaan
--      Source: 'Tab 10 (Kualitas Pembiayaan)'. Bulanan, NASIONAL,
--      per kategori (Total, Perseorangan, Badan Usaha, dst).
-- ---------------------------------------------------------------------
CREATE TABLE fact_p2p_kualitas_pembiayaan (
    kualitas_id         SMALLINT NOT NULL REFERENCES dim_kualitas_pembiayaan(kualitas_id),
    waktu_id            INTEGER  NOT NULL REFERENCES dim_waktu(waktu_id),
    jml_rek_penerima    BIGINT,
    outstanding_miliar  NUMERIC(14,2),
    source_sheet        VARCHAR(64) DEFAULT 'Tab 10 (Kualitas Pembiayaan)',
    loaded_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (kualitas_id, waktu_id)
);


-- ---------------------------------------------------------------------
-- D.3  fact_p2p_dana_diberikan
--      Source: 'Tab 5 (Dana Diberikan berdasarkan Lokasi)'.
--      Bulanan, per provinsi. Sisi LENDER (pemberi pinjaman).
-- ---------------------------------------------------------------------
CREATE TABLE fact_p2p_dana_diberikan (
    provinsi_id        SMALLINT NOT NULL REFERENCES dim_provinsi(provinsi_id),
    waktu_id           INTEGER  NOT NULL REFERENCES dim_waktu(waktu_id),
    jml_rek_pemberi    BIGINT,                 -- Jumlah Rekening Pemberi Pinjaman
    dana_diberikan_miliar NUMERIC(14,2),       -- Jumlah Dana yang Diberikan (miliar Rp)
    source_sheet       VARCHAR(64) DEFAULT 'Tab 5 (Dana Diberikan berdasark)',
    loaded_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (provinsi_id, waktu_id)
);


-- ---------------------------------------------------------------------
-- D.4  fact_p2p_penyaluran_sektor
--      Source: 'Tab 7 (Penyaluran ke Sektor Produktif)'.
--      Bulanan, NASIONAL, per sektor. Dalam miliar Rp.
-- ---------------------------------------------------------------------
CREATE TABLE fact_p2p_penyaluran_sektor (
    sektor_id           SMALLINT NOT NULL REFERENCES dim_sektor_produktif(sektor_id),
    waktu_id            INTEGER  NOT NULL REFERENCES dim_waktu(waktu_id),
    penyaluran_miliar   NUMERIC(14,2),
    source_sheet        VARCHAR(64) DEFAULT 'Tab 7 (Penyaluran ke Sektor Pro)',
    loaded_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (sektor_id, waktu_id)
);


-- =====================================================================
--  E. TABEL FAKTA - FISKAL & PERBANKAN
-- =====================================================================

-- ---------------------------------------------------------------------
-- E.1  fact_realisasi_tkd
--      Source: 'Realisasi TKD pertahun'. Tahunan, per Pemda (kab/kota).
--      Dinormalisasi ke LONG format (komponen_tkd) agar fleksibel.
-- ---------------------------------------------------------------------
CREATE TABLE fact_realisasi_tkd (
    pemda_id        INTEGER  NOT NULL REFERENCES dim_pemda(pemda_id),
    tahun           SMALLINT NOT NULL,
    status_data     VARCHAR(16) NOT NULL,       -- 'Realisasi' | 'Pagu' dll
    komponen_tkd    VARCHAR(32) NOT NULL,       -- 'DBH_Pajak','DAU_Block_Grant',...
    nilai_rp        NUMERIC(20,2),              -- semua komponen disatukan di sini
    source_sheet    VARCHAR(64) DEFAULT 'Realisasi TKD pertahun',
    loaded_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (pemda_id, tahun, status_data, komponen_tkd)
);

CREATE INDEX idx_tkd_tahun     ON fact_realisasi_tkd(tahun);
CREATE INDEX idx_tkd_komponen  ON fact_realisasi_tkd(komponen_tkd);


-- ---------------------------------------------------------------------
-- E.2  fact_perbankan
--      Source: 'Perbankan'. Per provinsi, snapshot (Des 2020, dst).
--      Sudah relatif tabular sehingga disimpan apa adanya.
-- ---------------------------------------------------------------------
CREATE TABLE fact_perbankan (
    provinsi_id        SMALLINT NOT NULL REFERENCES dim_provinsi(provinsi_id),
    tahun              SMALLINT NOT NULL,
    snapshot_label     VARCHAR(16) NOT NULL,      -- 'Des 2020', 'Des 2021', ...
    kredit_total_miliar NUMERIC(16,2),
    dpk_miliar          NUMERIC(16,2),
    ldr_pct             NUMERIC(8,4),
    zona_ldr            VARCHAR(16),              -- 'IDEAL','KRITIS','RENDAH', dll
    npl_miliar          NUMERIC(14,2),
    npl_ratio           NUMERIC(8,5),
    kredit_umkm_miliar  NUMERIC(14,2),
    rasio_umkm          NUMERIC(8,5),
    umkm_per_kc_miliar  NUMERIC(12,2),
    jml_kc_bank         INTEGER,
    source_sheet        VARCHAR(64) DEFAULT 'Perbankan',
    loaded_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (provinsi_id, tahun, snapshot_label)
);


-- =====================================================================
--  F. STAGING TABLES (untuk RAW import sebelum dibersihkan)
--     Pola: 1 staging per sheet, dtype longgar (TEXT) untuk tampung
--     anomali (mis. '2,38%' bercampur dengan 0.0238).
-- =====================================================================
CREATE TABLE stg_p2p_pinjaman_raw (
    provinsi        TEXT,
    bulan_tahun     TEXT,
    jml_rek_raw     TEXT,
    outstanding_raw TEXT,
    twp90_raw       TEXT,
    loaded_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE stg_pdrb_raw (
    provinsi    TEXT,
    tahun_raw   TEXT,
    pdrb_raw    TEXT,
    loaded_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- (staging untuk sheet lain mengikuti pola yang sama bila diperlukan)


-- =====================================================================
--  G. VIEW AGGREGAT - SIAP PAKAI UNTUK MODELLING
-- =====================================================================

-- ---------------------------------------------------------------------
-- G.1  vw_master_provinsi_bulanan
--      ONE BIG TABLE per (provinsi, bulan). Semua fitur level provinsi
--      dalam 1 baris. Indikator tahunan di-broadcast ke semua bulan
--      di tahun tsb. Indikator nasional (BI rate) di-broadcast ke
--      seluruh provinsi.
--      Ini biasanya yang langsung jadi training set.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_master_provinsi_bulanan AS
SELECT
    p.provinsi_id,
    p.nama_provinsi,
    w.tanggal,
    w.tahun,
    w.kuartal,
    w.bulan,

    -- ===== TARGET CANDIDATES =====
    pp.twp90,
    pp.outstanding_miliar          AS p2p_outstanding_miliar,
    pp.jml_rek_penerima            AS p2p_jml_rek_penerima,

    -- ===== P2P FEATURES (lender side) =====
    dd.dana_diberikan_miliar,
    dd.jml_rek_pemberi,

    -- ===== MAKRO NASIONAL =====
    br.bi_rate_pct,

    -- ===== MAKRO PROVINSI BULANAN =====
    inf.inflasi_yoy,

    -- ===== MAKRO PROVINSI TAHUNAN (broadcast) =====
    pdrb.pdrb_rp,
    pk.pdrb_per_kapita_rp,
    pen.penetrasi_pct,

    -- ===== TPT (semesteran -> ambil terdekat) =====
    -- Strategi: di view ini ambil TPT yg tahun = w.tahun & periode
    -- yg sesuai dengan posisi bulan (Jan-Jul -> Feb, Agu-Des -> Agt)
    tpt.tpt_pct
FROM dim_provinsi p
CROSS JOIN dim_waktu w
LEFT JOIN fact_p2p_pinjaman_provinsi pp
       ON pp.provinsi_id = p.provinsi_id AND pp.waktu_id = w.waktu_id
LEFT JOIN fact_p2p_dana_diberikan dd
       ON dd.provinsi_id = p.provinsi_id AND dd.waktu_id = w.waktu_id
LEFT JOIN fact_bi_rate br
       ON br.waktu_id = w.waktu_id
LEFT JOIN fact_inflasi_provinsi inf
       ON inf.provinsi_id = p.provinsi_id AND inf.waktu_id = w.waktu_id
LEFT JOIN fact_pdrb pdrb
       ON pdrb.provinsi_id = p.provinsi_id AND pdrb.tahun = w.tahun
LEFT JOIN fact_pdrb_per_kapita pk
       ON pk.provinsi_id = p.provinsi_id AND pk.tahun = w.tahun
LEFT JOIN fact_penetrasi_internet pen
       ON pen.provinsi_id = p.provinsi_id AND pen.tahun = w.tahun
LEFT JOIN fact_tpt tpt
       ON tpt.provinsi_id = p.provinsi_id
      AND tpt.tahun = w.tahun
      AND tpt.periode = CASE WHEN w.bulan <= 7 THEN 'Februari' ELSE 'Agustus' END;


-- ---------------------------------------------------------------------
-- G.2  vw_p2p_provinsi_quarterly
--      Rollup TWP90 & outstanding ke level kuartal (untuk model
--      yang tidak butuh granularitas bulanan).
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_p2p_provinsi_quarterly AS
SELECT
    pp.provinsi_id,
    p.nama_provinsi,
    w.tahun,
    w.kuartal,
    AVG(pp.twp90)                       AS twp90_avg,
    MAX(pp.twp90)                       AS twp90_max,
    SUM(pp.outstanding_miliar)          AS outstanding_total_miliar,
    AVG(pp.outstanding_miliar)          AS outstanding_avg_miliar,
    SUM(pp.jml_rek_penerima)            AS rek_penerima_total
FROM fact_p2p_pinjaman_provinsi pp
JOIN dim_waktu     w ON w.waktu_id = pp.waktu_id
JOIN dim_provinsi  p ON p.provinsi_id = pp.provinsi_id
GROUP BY pp.provinsi_id, p.nama_provinsi, w.tahun, w.kuartal;


-- ---------------------------------------------------------------------
-- G.3  vw_tkd_provinsi_tahunan
--      Agregasi TKD dari level Pemda (kab/kota) -> provinsi -> tahunan.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_tkd_provinsi_tahunan AS
SELECT
    pem.provinsi_id,
    prov.nama_provinsi,
    tkd.tahun,
    tkd.komponen_tkd,
    SUM(tkd.nilai_rp) AS total_nilai_rp
FROM fact_realisasi_tkd tkd
JOIN dim_pemda    pem  ON pem.pemda_id    = tkd.pemda_id
JOIN dim_provinsi prov ON prov.provinsi_id = pem.provinsi_id
WHERE tkd.status_data = 'Realisasi'
GROUP BY pem.provinsi_id, prov.nama_provinsi, tkd.tahun, tkd.komponen_tkd;


-- =====================================================================
--  H. CATATAN ETL / DATA QUALITY
-- =====================================================================
-- 1. Sheet 'Tab 9 (TWP90)' & 'Tab 10' & 'Tab 5' punya HEADER 2-LEVEL
--    (bulan-tahun di baris 1, metrik di baris 2). Saat ETL, pakai
--    pandas.read_excel(header=[0,1]) lalu unpivot (melt) ke long format.
--
-- 2. Beberapa cell TWP90 berisi string seperti '2,38%'. Standardisasi
--    di ETL: ganti koma->titik, hapus '%', bagi 100 jika perlu.
--    Simpan apa adanya di stg_*, simpan yg sudah bersih di fact_*.
--
-- 3. Sheet PDRB punya skala campuran (16e15 vs 184e12). Verifikasi
--    sumber & samakan satuan ke Rupiah penuh sebelum load.
--
-- 4. 'Realisasi TKD pertahun' menyimpan angka sebagai string dengan
--    pemisah ribuan titik (mis. '125.718.522.611'). Bersihkan dengan
--    REPLACE('.', '') -> CAST ke NUMERIC.
--
-- 5. Sheet 'Inflasi' punya dua skala: tahun 2021-2023 dalam %
--    (mis. 0.8 = 0.8%) tetapi 2024-2026 dalam rasio (0.0212 = 2.12%).
--    HARUS distandardisasi ke satu konvensi sebelum load. Disarankan:
--    semua disimpan sebagai DESIMAL (0.0212) di fact_inflasi_provinsi.
--
-- 6. Nama provinsi punya inkonsistensi case ('Dki Jakarta' vs
--    'DKI Jakarta'). Gunakan nama_provinsi_std (lowercase, trimmed)
--    untuk JOIN antar-sheet, lalu lookup ke provinsi_id.
--
-- 7. TPT 'Februari 2021' & 'Agustus 2021' bertipe object (mengandung
--    string). Bersihkan & cast ke NUMERIC saat ETL.
--
-- 8. Untuk modelling: pakai vw_master_provinsi_bulanan sebagai dataset
--    dasar. Lakukan feature engineering (lag, rolling mean, growth)
--    di Python/SQL setelah view ini.
-- =====================================================================

-- =====================================================================
--  I. CONTOH QUERY UNTUK MODELLING
-- =====================================================================
-- Contoh 1: Training set TWP90 sebagai target, fitur makro lengkap
-- ---------------------------------------------------------------------
-- SELECT *
-- FROM vw_master_provinsi_bulanan
-- WHERE tanggal BETWEEN '2021-01-01' AND '2025-12-01'
--   AND twp90 IS NOT NULL
-- ORDER BY provinsi_id, tanggal;
--
-- Contoh 2: Tambah TKD provinsi (rasio Dana Desa terhadap PDRB)
-- ---------------------------------------------------------------------
-- WITH tkd AS (
--   SELECT provinsi_id, tahun, total_nilai_rp AS dana_desa_rp
--   FROM vw_tkd_provinsi_tahunan
--   WHERE komponen_tkd = 'Dana_Desa'
-- )
-- SELECT m.*,
--        t.dana_desa_rp,
--        t.dana_desa_rp / NULLIF(m.pdrb_rp,0) AS rasio_dana_desa_pdrb
-- FROM vw_master_provinsi_bulanan m
-- LEFT JOIN tkd t ON t.provinsi_id = m.provinsi_id AND t.tahun = m.tahun;
--
-- Contoh 3: Lag fitur TWP90 (untuk model time-series)
-- ---------------------------------------------------------------------
-- SELECT
--   provinsi_id, tanggal, twp90,
--   LAG(twp90, 1) OVER (PARTITION BY provinsi_id ORDER BY tanggal) AS twp90_lag1,
--   LAG(twp90, 3) OVER (PARTITION BY provinsi_id ORDER BY tanggal) AS twp90_lag3,
--   AVG(twp90) OVER (PARTITION BY provinsi_id ORDER BY tanggal
--                    ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING) AS twp90_ma6
-- FROM fact_p2p_pinjaman_provinsi pp
-- JOIN dim_waktu w USING (waktu_id);
-- =====================================================================
