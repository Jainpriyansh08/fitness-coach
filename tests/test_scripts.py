#!/usr/bin/env python3
"""Automated checks for the coach skills: the workbook scripts and the skill wiring.

Run from the repository root:  python tests/test_scripts.py
Needs Python 3 + openpyxl. Formula recalculation checks run only if LibreOffice is installed.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
MAIN = SKILLS / "fitness-lifestyle-coach"
BUILD = MAIN / "scripts" / "build_workbook.py"
READ = MAIN / "scripts" / "read_workbook.py"
CHECK = MAIN / "scripts" / "check_workbook.py"
COACH_ONLY = {"Coach Notes", "Evidence & Sources", "Decision Log", "_plan_data"}
SOFFICE = shutil.which("soffice") or shutil.which("libreoffice")

results: list[tuple[str, bool, str]] = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))


def run(*args, **kw):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, **kw)


def recalc(path: Path, outdir: Path) -> Path:
    subprocess.run([SOFFICE, "--headless", "--calc", "--convert-to", "xlsx:Calc MS Excel 2007 XML",
                    "--outdir", str(outdir), str(path)], capture_output=True, timeout=240)
    return outdir / path.name


def test_build_examples(tmp: Path):
    for example in ("example-plan.json", "example-plan-structured.json"):
        out = tmp / example.replace(".json", "")
        r = run(BUILD, MAIN / "assets" / example, "--out-dir", out)
        check(f"build {example}", r.returncode == 0, r.stderr[-400:])
        files = sorted(out.glob("*.xlsx"))
        check(f"{example}: two copies written", len(files) == 2, [f.name for f in files])
        coach = next((f for f in files if "(Coach)" in f.name), None)
        client = next((f for f in files if "(Coach)" not in f.name), None)
        if not (coach and client):
            continue
        wc, wl = load_workbook(coach), load_workbook(client)
        check(f"{example}: coach copy has coach-only tabs", COACH_ONLY <= set(wc.sheetnames))
        check(f"{example}: client copy has no coach-only tabs", not (COACH_ONLY & set(wl.sheetnames)),
              sorted(COACH_ONLY & set(wl.sheetnames)))
        check(f"{example}: _plan_data hidden", wc["_plan_data"].sheet_state == "hidden")
        for tab in ("Overview", "Check-in Tracker", "Weekly Summary", "Measurements", "Change Log"):
            check(f"{example}: client copy has {tab}", tab in wl.sheetnames)
        # plan JSON round trip
        pj = tmp / f"{example}.roundtrip.json"
        r = run(READ, coach, "--plan-json", pj)
        original = json.loads((MAIN / "assets" / example).read_text(encoding="utf-8"))
        check(f"{example}: plan JSON round-trips", r.returncode == 0 and pj.exists()
              and json.loads(pj.read_text(encoding="utf-8")) == original)
        # measurement unit selector
        m = wl["Measurements"]
        unit_rows = [row for row in range(1, m.max_row + 1) if m.cell(row, 1).value == "I measure in (choose cm or in):"]
        check(f"{example}: Measurements has a cm/in selector", len(unit_rows) == 1)
        if SOFFICE:
            r = run(CHECK, coach, client)
            check(f"{example}: all formulas calculate (LibreOffice)", r.returncode == 0, r.stdout[-600:])


def test_units_conversion(tmp: Path):
    if not SOFFICE:
        check("units conversion (skipped: no LibreOffice)", True)
        return
    out = tmp / "units"
    run(BUILD, MAIN / "assets" / "example-plan.json", "--out-dir", out, "--copy", "client")
    src = next(out.glob("*.xlsx"))
    for unit, values, expect in (("cm", (90, 88.5), (35.4, 34.8, -0.6)), ("in", (35.5, 34.8), (90.2, 88.4, -1.8))):
        wb = load_workbook(src)
        m = wb["Measurements"]
        ur = next(r for r in range(1, m.max_row + 1) if m.cell(r, 1).value == "I measure in (choose cm or in):")
        m.cell(ur, 2).value = unit
        waist = next(r for r in range(ur, m.max_row + 1) if m.cell(r, 1).value == "Waist (at navel)")
        m.cell(waist, 3).value, m.cell(waist, 4).value = values
        p = tmp / f"units_{unit}.xlsx"
        wb.save(p)
        v = load_workbook(recalc(p, tmp / f"conv_{unit}"), data_only=True)["Measurements"]
        conv = [r for r in range(1, v.max_row + 1) if v.cell(r, 1).value == "Waist (at navel)"][-1]
        got = (v.cell(conv, 3).value, v.cell(conv, 4).value)
        tot_col = next(c for c in range(1, v.max_column + 1) if v.cell(ur + 2, c).value == "Total change")
        got_total = round(v.cell(conv, tot_col).value, 1)
        check(f"units: entered in {unit}, converted values correct", got == expect[:2] and got_total == expect[2],
              f"got {got} total {got_total}, expected {expect}")


def test_sanitiser_and_validation(tmp: Path):
    plan = json.loads((MAIN / "assets" / "example-plan-structured.json").read_text(encoding="utf-8"))
    plan["nutrition"]["targets"][0]["target"] = "=1900 kcal"
    p = tmp / "sanitise.json"
    p.write_text(json.dumps(plan), encoding="utf-8")
    r = run(BUILD, p, "--out-dir", tmp / "san", "--copy", "client")
    ok = False
    if r.returncode == 0:
        wb = load_workbook(next((tmp / "san").glob("*.xlsx")))
        ok = any(c.value == " =1900 kcal" and c.data_type == "s"
                 for row in wb["Nutrition"].iter_rows() for c in row)
    check("text starting with '=' is kept as text, not a formula", ok, r.stderr[-300:])
    plan["supplements"]["items"].append({"name": "Mystery herb"})
    p.write_text(json.dumps(plan), encoding="utf-8")
    r = run(BUILD, p, "--out-dir", tmp / "bad")
    check("supplement without evidence/cautions is rejected", r.returncode != 0 and "evidence" in (r.stderr + r.stdout))


def test_read_workbook_digest(tmp: Path):
    out = tmp / "digest"
    run(BUILD, MAIN / "assets" / "example-plan.json", "--out-dir", out, "--copy", "client")
    src = next(out.glob("*.xlsx"))
    wb = load_workbook(src)
    t = wb["Check-in Tracker"]
    hdr = next(r for r in range(1, t.max_row + 1) if t.cell(r, 1).value == "Date")
    for d in range(7):
        t.cell(hdr + 1 + d, 4).value = "Y" if d % 2 == 0 else "N"
        t.cell(hdr + 1 + d, 5).value = 72.0 - d * 0.1
    t.cell(hdr + 2, 12).value = "Left knee 3/10 on lunges"
    p = tmp / "digest_filled.xlsx"
    wb.save(p)
    r = run(READ, p, "--checkins")
    check("read_workbook --checkins digests the week", r.returncode == 0 and "sessions done 4" in r.stdout
          and "Left knee" in r.stdout, r.stdout[-500:])


def test_skill_wiring():
    r = run(ROOT / "tools" / "sync_skills.py", "--check")
    check("skills are in sync with the main skill (tools/sync_skills.py --check)", r.returncode == 0, r.stdout[-800:])
    for sdir in sorted(SKILLS.iterdir()):
        if not (sdir / "SKILL.md").exists():
            continue
        text = (sdir / "SKILL.md").read_text(encoding="utf-8")
        m = re.match(r"^---\nname: (.+?)\ndescription: (.+?)\n---\n", text, re.S)
        check(f"{sdir.name}: frontmatter name matches folder", bool(m) and m.group(1).strip() == sdir.name)
        check(f"{sdir.name}: description ≤ 1024 chars", bool(m) and len(m.group(2)) <= 1024)
        missing = sorted({ref for ref in re.findall(r"`((?:references|scripts|assets)/[\w.\-]+)`", text)
                          if not (sdir / ref).exists()})
        check(f"{sdir.name}: every file the SKILL.md names exists", not missing, missing)
        check(f"{sdir.name}: shared ground rules present", "## Ground rules (shared by every coach skill)" in text)


def main():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        test_build_examples(tmp)
        test_units_conversion(tmp)
        test_sanitiser_and_validation(tmp)
        test_read_workbook_digest(tmp)
        test_skill_wiring()
    width = max(len(n) for n, _, _ in results)
    failed = 0
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name.ljust(width)}" + ("" if ok or not detail else f"  -> {detail}"))
        failed += not ok
    print(f"\n{len(results) - failed}/{len(results)} checks passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
