"""
ETL script to generate model panel dataframe from XLSX.
Output: CSV with columns per designed schema (province_norm, ym, target + 10 features + auxiliary).
"""

import json
import re
from datetime import datetime, timedelta
from collections import defaultdict
import pandas as pd
import numpy as np
from openpyxl import load_workbook

XLSX_PATH = r"c:\Users\bimyu\Documents\Projects\DatathonMETC\data prep datathon dicoding.xlsx"
OUTPUT_CSV = r"c:\Users\bimyu\Documents\Projects\DatathonMETC\model_panel_template.csv"

# ============ UTILITY FUNCTIONS ============

def normalize_province(name):
    """Normalize province name to lowercase, remove prefixes, exclude Papua."""
    if name is None:
        return None
    s = str(name).strip().lower()
    s = re.sub(r"^(kab\.|kabupaten|kota|provinsi)", "", s)
    s = s.replace("prov.", "").strip()
    s = re.sub(r"\s+", " ", s)
    if "papua" in s:
        return None
    return s

def parse_month_year(label):
    """Parse month-year from various formats (Jan 21, 2026-01-21, Februari 2021, etc.)."""
    if label is None:
        return None
    
    # Handle datetime objects
    if hasattr(label, "year") and hasattr(label, "month"):
        return f"{label.year:04d}-{label.month:02d}"
    
    s = str(label).strip().lower()
    
    # Extract year (support 2026, 2021, 21, 22, etc.)
    year = None
    year_match_full = re.search(r"(20\d{2})", s)
    year_match_short = re.search(r"\b(\d{2})\b", s)
    
    if year_match_full:
        year = int(year_match_full.group(1))
    elif year_match_short:
        yy = int(year_match_short.group(1))
        # Assume 00-50 → 2000-2050, 51-99 → 1951-1999
        year = 2000 + yy if yy <= 50 else 1900 + yy
    else:
        return None
    
    # Extract month
    month_map = {
        "jan": 1, "januari": 1, "feb": 2, "februari": 2, "mar": 3, "maret": 3,
        "apr": 4, "april": 4, "mei": 5, "jun": 6, "juni": 6, "jul": 7, "juli": 7,
        "agu": 8, "agustus": 8, "sep": 9, "sept": 9, "september": 9,
        "okt": 10, "oktober": 10, "nov": 11, "november": 11, "des": 12, "desember": 12
    }
    
    month = None
    for token in re.split(r"[^a-z0-9]+", s):
        if token in month_map:
            month = month_map[token]
            break
    
    if month is None:
        return None
    
    return f"{year:04d}-{month:02d}"

def date_range(start_ym, end_ym):
    """Generate list of YYYY-MM strings from start to end (inclusive)."""
    start_year, start_month = map(int, start_ym.split("-"))
    end_year, end_month = map(int, end_ym.split("-"))
    
    dates = []
    y, m = start_year, start_month
    while (y, m) <= (end_year, end_month):
        dates.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            m = 1
            y += 1
    return dates

# ============ LOAD XLSX ============

wb = load_workbook(XLSX_PATH, data_only=True, read_only=True)
sheets = {ws.title: ws for ws in wb.worksheets}

# Find sheets by pattern
sheet_map = {}
for name in sheets:
    lname = name.lower()
    if lname.startswith("tab 9"):
        sheet_map["target_twp90"] = name
    elif lname == "bi rate":
        sheet_map["bi_rate"] = name
    elif lname.startswith("inflasi"):
        sheet_map["inflasi"] = name
    elif lname.startswith("pdrb per kapita"):
        sheet_map["pdrb_pc"] = name
    elif lname.startswith("tingkat pengangguran terbuka"):
        sheet_map["tpt"] = name
    elif lname.startswith("tingkat penetrasi internet"):
        sheet_map["internet"] = name
    elif lname == "perbankan":
        sheet_map["perbankan"] = name

print(f"Found sheets: {sheet_map}")

# ============ BUILD MASTER PROVINCE LIST ============

def get_provinces_from_sheet(sheet_name, data_start_row=2, prov_col=0):
    """Extract normalized province list from sheet."""
    ws = sheets[sheet_name]
    provs = set()
    for row in ws.iter_rows(min_row=data_start_row, values_only=True):
        if not row or len(row) <= prov_col:
            continue
        p = row[prov_col]
        if p in (None, ""):
            continue
        pn = normalize_province(p)
        if pn and pn not in ("total", "indonesia", "nasional"):
            provs.add(pn)
    return sorted(provs)

target_provs = get_provinces_from_sheet(sheet_map["target_twp90"], data_start_row=3, prov_col=0)
print(f"Target provinces (excluding Papua): {len(target_provs)} — {target_provs[:5]}...")

# ============ MASTER PANEL ============

target_period_start = "2021-01"
target_period_end = "2025-12"
all_months = date_range(target_period_start, target_period_end)

master_index = []
for prov in target_provs:
    for ym in all_months:
        year, month = map(int, ym.split("-"))
        master_index.append({
            "province_norm": prov,
            "ym": ym,
            "year": year,
            "month": month
        })

panel_df = pd.DataFrame(master_index)
print(f"Master panel shape: {panel_df.shape} ({len(target_provs)} provinces × {len(all_months)} months)")

# ============ EXTRACT & JOIN FEATURES ============

# --- x1: BI Rate (national, monthly) ---
ws_bi = sheets[sheet_map["bi_rate"]]
bi_data = {}
bi_rows = list(ws_bi.iter_rows(values_only=True))
bi_header = bi_rows[0] if bi_rows else []

for year_idx, year_label in enumerate(bi_header[1:], start=1):
    if year_label is None:
        continue
    try:
        year = int(re.search(r"(20\d{2})", str(year_label)).group(1))
    except:
        continue
    
    for month_idx, row in enumerate(bi_rows[1:], start=1):
        if month_idx > 12 or len(row) <= year_idx:
            continue
        val = row[year_idx]
        if val not in (None, "") and isinstance(val, (int, float)):
            ym = f"{year:04d}-{month_idx:02d}"
            bi_data[ym] = float(val)

panel_df["x1_bi_rate_pct"] = panel_df["ym"].map(bi_data).astype("float64")
print(f"x1_bi_rate_pct filled: {panel_df['x1_bi_rate_pct'].notna().sum()} rows")

# --- x2: Inflasi (monthly, per province) ---
ws_inf = sheets[sheet_map["inflasi"]]
inflasi_data = {}
inf_rows = list(ws_inf.iter_rows(values_only=True))
inf_header = inf_rows[0] if inf_rows else []

for col_idx, col_label in enumerate(inf_header[1:], start=1):
    ym = parse_month_year(col_label)
    if ym is None:
        continue
    
    for row_idx, row in enumerate(inf_rows[1:], start=1):
        if len(row) <= col_idx:
            continue
        prov_name = normalize_province(row[0]) if row else None
        val = row[col_idx]
        
        if prov_name and val not in (None, "") and isinstance(val, (int, float)):
            key = (prov_name, ym)
            inflasi_data[key] = float(val)

def get_inflasi(prov, ym):
    return inflasi_data.get((prov, ym), np.nan)

panel_df["x2_inflasi_mtom_pct"] = panel_df.apply(
    lambda r: get_inflasi(r["province_norm"], r["ym"]), axis=1
).astype("float64")
print(f"x2_inflasi_mtom_pct filled: {panel_df['x2_inflasi_mtom_pct'].notna().sum()} rows")

# --- x3: PDRB Per Kapita (yearly, per province) → expand to monthly ---
ws_pdrb = sheets[sheet_map["pdrb_pc"]]
pdrb_data = defaultdict(dict)
pdrb_rows = list(ws_pdrb.iter_rows(values_only=True))
pdrb_header = pdrb_rows[0] if pdrb_rows else []

for col_idx, year_label in enumerate(pdrb_header[1:], start=1):
    try:
        year = int(re.search(r"(20\d{2})", str(year_label)).group(1))
    except:
        continue
    
    for row in pdrb_rows[1:]:
        if len(row) <= col_idx:
            continue
        prov_name = normalize_province(row[0]) if row else None
        val = row[col_idx]
        
        if prov_name and val not in (None, "") and isinstance(val, (int, float)):
            pdrb_data[prov_name][year] = float(val)

def get_pdrb_monthly(prov, year, month):
    """Return PDRB for year; same value for all months of that year."""
    return pdrb_data.get(prov, {}).get(year, np.nan)

panel_df["x3_pdrb_per_kapita"] = panel_df.apply(
    lambda r: get_pdrb_monthly(r["province_norm"], r["year"], r["month"]), axis=1
).astype("float64")
panel_df["imputed_pdrb"] = panel_df["x3_pdrb_per_kapita"].notna()
print(f"x3_pdrb_per_kapita filled: {panel_df['x3_pdrb_per_kapita'].notna().sum()} rows")

# --- x4: TPT (semiannual, per province) → expand to monthly (linear interp) ---
ws_tpt = sheets[sheet_map["tpt"]]
tpt_data = defaultdict(list)
tpt_rows = list(ws_tpt.iter_rows(values_only=True))
tpt_header = tpt_rows[0] if tpt_rows else []

tpt_periods = []
for col_idx, col_label in enumerate(tpt_header[1:], start=1):
    ym = parse_month_year(col_label)
    if ym:
        tpt_periods.append((col_idx, ym))

for row in tpt_rows[1:]:
    if not row:
        continue
    prov_name = normalize_province(row[0]) if row else None
    if not prov_name:
        continue
    
    for col_idx, ym in tpt_periods:
        if len(row) <= col_idx:
            continue
        val = row[col_idx]
        if val not in (None, "") and isinstance(val, (int, float)):
            tpt_data[prov_name].append((ym, float(val)))

def get_tpt_monthly(prov, ym):
    """For semiannual TPT, use last known value (forward fill) or NaN."""
    data_points = sorted(tpt_data.get(prov, []))
    if not data_points:
        return np.nan
    
    for (known_ym, val) in data_points:
        if known_ym == ym:
            return val
    
    # Forward fill: use last known value before or at this month
    for (known_ym, val) in reversed(data_points):
        if known_ym <= ym:
            return val
    
    return np.nan

panel_df["x4_tpt_pct"] = panel_df.apply(
    lambda r: get_tpt_monthly(r["province_norm"], r["ym"]), axis=1
).astype("float64")
panel_df["imputed_tpt"] = panel_df["x4_tpt_pct"].notna()
print(f"x4_tpt_pct filled: {panel_df['x4_tpt_pct'].notna().sum()} rows")

# --- x5: Penetrasi Internet (yearly, per province) → expand to monthly ---
ws_inet = sheets[sheet_map["internet"]]
inet_data = defaultdict(dict)
inet_rows = list(ws_inet.iter_rows(values_only=True))
# Internet sheet has header at row 1 (index 1), data starts at row 2
inet_header = inet_rows[1] if len(inet_rows) > 1 else []

for col_idx, year_label in enumerate(inet_header[1:], start=1):
    try:
        year = int(re.search(r"(20\d{2})", str(year_label)).group(1))
    except:
        continue
    
    for row in inet_rows[2:]:
        if not row or len(row) <= col_idx:
            continue
        prov_name = normalize_province(row[0]) if row else None
        val = row[col_idx]
        
        if prov_name and val not in (None, "") and isinstance(val, (int, float)):
            inet_data[prov_name][year] = float(val)

def get_inet_monthly(prov, year, month):
    """Return internet penetration for year; same value for all months."""
    return inet_data.get(prov, {}).get(year, np.nan)

panel_df["x5_penetrasi_internet_pct"] = panel_df.apply(
    lambda r: get_inet_monthly(r["province_norm"], r["year"], r["month"]), axis=1
).astype("float64")
panel_df["imputed_internet"] = panel_df["x5_penetrasi_internet_pct"].notna()
print(f"x5_penetrasi_internet_pct filled: {panel_df['x5_penetrasi_internet_pct'].notna().sum()} rows")

# --- x6..x10: Perbankan (yearly snapshot, per province) ---
ws_pb = sheets[sheet_map["perbankan"]]
pb_rows = list(ws_pb.iter_rows(values_only=True))
pb_h2 = pb_rows[1] if len(pb_rows) > 1 else []

# Find column indices
col_map = {}
for idx, header in enumerate(pb_h2):
    if header is None:
        continue
    h_lower = str(header).lower().replace("\n", " ").strip()
    if "dpk" in h_lower or "tabungan" in h_lower:
        col_map["dpk"] = idx
    if "ldr" in h_lower:
        col_map["ldr"] = idx
    if "npl ratio" in h_lower:
        col_map["npl"] = idx
    if "rasio umkm" in h_lower:
        col_map["rasio_umkm"] = idx
    if "jml kc" in h_lower or "kc" in h_lower:
        col_map["kc"] = idx

# Extract perbankan data (assume columns: Kode BPS, Provinsi, Tahun, Snapshot, ...)
pb_data = defaultdict(lambda: defaultdict(dict))
for row in pb_rows[2:]:
    if not row or len(row) < 3:
        continue
    prov_name = normalize_province(row[1]) if len(row) > 1 else None
    try:
        year = int(float(row[2])) if len(row) > 2 and row[2] not in (None, "") else None
    except:
        year = None
    
    if not prov_name or year is None:
        continue
    
    if "dpk" in col_map and len(row) > col_map["dpk"]:
        val = row[col_map["dpk"]]
        if val not in (None, "") and isinstance(val, (int, float)):
            pb_data[prov_name][year]["dpk"] = float(val)
    
    if "ldr" in col_map and len(row) > col_map["ldr"]:
        val = row[col_map["ldr"]]
        if val not in (None, "") and isinstance(val, (int, float)):
            pb_data[prov_name][year]["ldr"] = float(val)
    
    if "npl" in col_map and len(row) > col_map["npl"]:
        val = row[col_map["npl"]]
        if val not in (None, "") and isinstance(val, (int, float)):
            pb_data[prov_name][year]["npl"] = float(val)
    
    if "rasio_umkm" in col_map and len(row) > col_map["rasio_umkm"]:
        val = row[col_map["rasio_umkm"]]
        if val not in (None, "") and isinstance(val, (int, float)):
            pb_data[prov_name][year]["rasio_umkm"] = float(val)
    
    if "kc" in col_map and len(row) > col_map["kc"]:
        val = row[col_map["kc"]]
        if val not in (None, "") and isinstance(val, (int, float)):
            pb_data[prov_name][year]["kc"] = int(float(val))

def get_pb_feature(prov, year, feature_key):
    return pb_data.get(prov, {}).get(year, {}).get(feature_key, np.nan)

panel_df["x6_tabungan_miliar"] = panel_df.apply(
    lambda r: get_pb_feature(r["province_norm"], r["year"], "dpk"), axis=1
).astype("float64")

panel_df["x7_jumlah_kc_bank"] = panel_df.apply(
    lambda r: get_pb_feature(r["province_norm"], r["year"], "kc"), axis=1
).astype("Int64")  # nullable int

panel_df["x8_ldr_pct"] = panel_df.apply(
    lambda r: get_pb_feature(r["province_norm"], r["year"], "ldr"), axis=1
).astype("float64")

panel_df["x9_npl_ratio_pct"] = panel_df.apply(
    lambda r: get_pb_feature(r["province_norm"], r["year"], "npl"), axis=1
).astype("float64")

panel_df["x10_rasio_umkm_pct"] = panel_df.apply(
    lambda r: get_pb_feature(r["province_norm"], r["year"], "rasio_umkm"), axis=1
).astype("float64")

panel_df["imputed_perbanking"] = (
    panel_df["x6_tabungan_miliar"].notna() | 
    panel_df["x7_jumlah_kc_bank"].notna() | 
    panel_df["x8_ldr_pct"].notna() |
    panel_df["x9_npl_ratio_pct"].notna() | 
    panel_df["x10_rasio_umkm_pct"].notna()
)
print(f"Perbankan features filled: {panel_df['x6_tabungan_miliar'].notna().sum()}, {panel_df['x7_jumlah_kc_bank'].notna().sum()}, {panel_df['x8_ldr_pct'].notna().sum()}, {panel_df['x9_npl_ratio_pct'].notna().sum()}, {panel_df['x10_rasio_umkm_pct'].notna().sum()}")

# --- TARGET: TWP90 ---
ws_target = sheets[sheet_map["target_twp90"]]
target_rows = list(ws_target.iter_rows(values_only=True))
target_h1 = target_rows[0] if target_rows else []
target_h2 = target_rows[1] if len(target_rows) > 1 else []

# Find TWP90 columns
twp_cols = []
for col_idx in range(1, len(target_h2)):
    h2_val = target_h2[col_idx] if col_idx < len(target_h2) else None
    if h2_val and "twp" in str(h2_val).lower():
        twp_cols.append(col_idx)

# Parse month labels (handle merged headers)
twp_months = []
for col_idx in twp_cols:
    label = target_h1[col_idx] if col_idx < len(target_h1) else None
    if label in (None, ""):
        # Backtrack for merged header
        for j in range(col_idx - 1, -1, -1):
            back = target_h1[j] if j < len(target_h1) else None
            if back not in (None, ""):
                label = back
                break
    
    ym = parse_month_year(label)
    if ym:
        twp_months.append((col_idx, ym))

target_data = defaultdict(dict)
for row in target_rows[2:]:
    if not row:
        continue
    prov_name = normalize_province(row[0]) if row else None
    if not prov_name or prov_name not in target_provs:
        continue
    
    for col_idx, ym in twp_months:
        if len(row) <= col_idx:
            continue
        val = row[col_idx]
        if val not in (None, "") and isinstance(val, (int, float)):
            target_data[prov_name][ym] = float(val)

def get_target(prov, ym):
    return target_data.get(prov, {}).get(ym, np.nan)

panel_df["twp90_pct"] = panel_df.apply(
    lambda r: get_target(r["province_norm"], r["ym"]), axis=1
).astype("float64")
print(f"twp90_pct (target) filled: {panel_df['twp90_pct'].notna().sum()} rows")

# ============ FINAL CLEANUP & SAVE ============

# Column order per schema
final_cols = [
    "province_norm", "ym", "year", "month",
    "twp90_pct",  # target
    "x1_bi_rate_pct", "x2_inflasi_mtom_pct", "x3_pdrb_per_kapita", "x4_tpt_pct",
    "x5_penetrasi_internet_pct", "x6_tabungan_miliar", "x7_jumlah_kc_bank",
    "x8_ldr_pct", "x9_npl_ratio_pct", "x10_rasio_umkm_pct",
    "imputed_pdrb", "imputed_tpt", "imputed_internet", "imputed_perbanking",
    "source_missing_perbanking"
]

panel_df["source_missing_perbanking"] = ~panel_df["imputed_perbanking"]

panel_df = panel_df[final_cols]

# Save
panel_df.to_csv(OUTPUT_CSV, index=False, float_format="%.6f")
print(f"\n✓ CSV saved to: {OUTPUT_CSV}")
print(f"Shape: {panel_df.shape}")
print(f"\nDataFrame info:")
print(panel_df.info())
print(f"\nFirst 10 rows:")
print(panel_df.head(10))
print(f"\nMissing values per column:")
print(panel_df.isnull().sum())

wb.close()
