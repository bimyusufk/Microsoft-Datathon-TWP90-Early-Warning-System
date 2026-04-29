"""
Eksplorasi struktur sheet "Realisasi TKD pertahun" dari XLSX.
"""
from openpyxl import load_workbook

XLSX_PATH = r"c:\Users\bimyu\Documents\Projects\DatathonMETC\data prep datathon dicoding.xlsx"

wb = load_workbook(XLSX_PATH, data_only=True, read_only=True)
ws = wb["Realisasi TKD pertahun"]
rows = list(ws.iter_rows(values_only=True))
wb.close()

lines = []
lines.append(f"Total rows: {len(rows)}")
lines.append(f"Max cols: {max(len(r) for r in rows[:10])}")

lines.append("\n=== ROW 1 (header) ===")
for i, v in enumerate(rows[0]):
    if v is not None:
        lines.append(f"  col[{i:>2}] = {repr(v)}")

lines.append("\n=== ROW 2 ===")
for i, v in enumerate(rows[1]):
    if v is not None:
        lines.append(f"  col[{i:>2}] = {repr(v)}")

lines.append("\n=== DATA ROWS 2-6 (raw) ===")
for row in rows[1:6]:
    lines.append(str(row)[:200])

lines.append("\n=== LAST 3 ROWS ===")
for row in rows[-3:]:
    lines.append(str(row)[:200])

# Distinct status_data
statuses = set()
id_col, nama_col = None, None
# Identify column positions from header
for i, v in enumerate(rows[0]):
    if v == "ID_Pemda": id_col = i
    if v == "Nama_Pemda": nama_col = i

lines.append(f"\nID_Pemda col index: {id_col}, Nama_Pemda col index: {nama_col}")

# Cek semua kolom header
lines.append("\nSemua kolom header (row 1):")
for i, v in enumerate(rows[0]):
    lines.append(f"  [{i}] {repr(v)}")

# Sample tahun unik
tahuns = set()
for row in rows[1:]:
    if row and len(row) > 2 and row[2] not in (None, ""):
        try:
            tahuns.add(int(float(str(row[2]))))
        except:
            pass
lines.append(f"\nTahun unik: {sorted(tahuns)}")

# Total non-empty rows
valid = [r for r in rows[1:] if r and r[0] not in (None, "")]
lines.append(f"Baris valid (col 0 tidak kosong): {len(valid)}")

output = "\n".join(lines)
print(output)
with open("tkd_explore.txt", "w", encoding="utf-8") as f:
    f.write(output)
print("\n[Saved to tkd_explore.txt]")
