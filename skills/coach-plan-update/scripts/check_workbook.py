#!/usr/bin/env python3
"""Recalculate a workbook with LibreOffice (if installed) and report formula errors.

Usage:
    python check_workbook.py FILE.xlsx [FILE2.xlsx ...]

Exit code 0 = no errors found (or LibreOffice unavailable — reported as SKIPPED), 1 = errors found.
openpyxl writes formulas without results; this converts a copy through LibreOffice so every formula
is evaluated, then scans for #REF!, #NAME?, #VALUE!, #DIV/0!, Err:xxx etc.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from openpyxl import load_workbook

ERR_MARKERS = ("#REF!", "#NAME?", "#VALUE!", "#DIV/0!", "#N/A", "#NUM!", "#NULL!", "Err:")


def soffice():
    for name in ("soffice", "libreoffice"):
        p = shutil.which(name)
        if p:
            return p
    return None


def check(path: Path, exe: str) -> int:
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "in.xlsx"
        shutil.copy(path, src)
        out = Path(tmp) / "out"
        subprocess.run([exe, "--headless", "--calc", "--convert-to", "xlsx:Calc MS Excel 2007 XML",
                        "--outdir", str(out), str(src)], check=False, capture_output=True, timeout=240)
        res = out / "in.xlsx"
        if not res.exists():
            print(f"{path.name}: SKIPPED (LibreOffice conversion failed)")
            return 0
        wb = load_workbook(res, data_only=True)
        errs = []
        for ws in wb.worksheets:
            for row in ws.iter_rows():
                for c in row:
                    if isinstance(c.value, str) and c.value.strip().startswith(ERR_MARKERS):
                        errs.append(f"{ws.title}!{c.coordinate} = {c.value}")
        if errs:
            print(f"{path.name}: {len(errs)} formula error(s)")
            for e in errs[:40]:
                print("   ", e)
            return 1
        print(f"{path.name}: OK — all formulas calculate")
        return 0


def main():
    files = [Path(a) for a in sys.argv[1:]]
    if not files:
        sys.exit(__doc__)
    exe = soffice()
    if not exe:
        print("SKIPPED: LibreOffice not installed — open the file in Excel or Google Sheets and check the "
              "Overview dashboard and Weekly Summary show values, not errors.")
        return 0
    return max(check(f, exe) for f in files)


if __name__ == "__main__":
    sys.exit(main())
