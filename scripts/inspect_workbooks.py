"""Structural inspection of the three primary emission-factor workbooks.

Writes:
  docs/DATA_INSPECTION.md          human-readable report
  data/processed/inspection.json   machine-readable dictionary
Assumes nothing about sheet names, header rows or column names.
"""
import json, os, sys, re
from pathlib import Path
import openpyxl

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "CEA":   ROOT / "data/raw/cea/Baseline_Carbon_Dioxide_Emission_Database_Version_22.0.xlsx",
    "EPA":   ROOT / "data/raw/epa/ghg-emission-factors-hub-2025.xlsx",
    "UK2026":ROOT / "data/raw/uk2026/ghg-conversion-factors-2026-full-set.xlsx",
}

def cell_repr(v):
    if v is None: return None
    s = str(v).strip()
    s = re.sub(r"\s+", " ", s)
    return s[:120] if s else None

def inspect(path):
    wb = openpyxl.load_workbook(path, data_only=True, read_only=False)
    out = {"file": path.name, "sheets": []}
    for ws in wb.worksheets:
        info = {
            "name": ws.title,
            "state": ws.sheet_state,
            "max_row": ws.max_row,
            "max_col": ws.max_column,
            "merged": [str(r) for r in list(ws.merged_cells.ranges)[:25]],
            "merged_count": len(ws.merged_cells.ranges),
            "hidden_rows": [r for r, d in ws.row_dimensions.items() if d.hidden][:20],
            "hidden_cols": [c for c, d in ws.column_dimensions.items() if d.hidden][:20],
        }
        # first 18 rows x first 14 cols preview
        preview = []
        for r in range(1, min(ws.max_row, 18) + 1):
            row = [cell_repr(ws.cell(row=r, column=c).value) for c in range(1, min(ws.max_column, 14) + 1)]
            if any(x is not None for x in row):
                preview.append({"row": r, "cells": row})
        info["preview"] = preview
        # density per row for first 40 rows -> helps locate the header row
        dens = []
        for r in range(1, min(ws.max_row, 40) + 1):
            n = sum(1 for c in range(1, ws.max_column + 1) if ws.cell(row=r, column=c).value not in (None, ""))
            dens.append(n)
        info["row_density_first40"] = dens
        out["sheets"].append(info)
    wb.close()
    return out

def main():
    (ROOT / "data/processed").mkdir(parents=True, exist_ok=True)
    report = {}
    for key, p in SOURCES.items():
        print(f"inspecting {key} ...", file=sys.stderr)
        report[key] = inspect(p)
    (ROOT / "data/processed/inspection.json").write_text(json.dumps(report, indent=1))
    # summary to stdout
    for key, rep in report.items():
        print(f"\n===== {key} :: {rep['file']} =====")
        for s in rep["sheets"]:
            print(f"  [{s['state']}] {s['name']!r}  rows={s['max_row']} cols={s['max_col']} merged={s['merged_count']}")
    print("\nwrote data/processed/inspection.json")

main()
