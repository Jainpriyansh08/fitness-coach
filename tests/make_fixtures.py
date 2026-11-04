#!/usr/bin/env python3
"""Build the filled-in client workbooks used by the check-in and plan-update eval cases.

Run from the repository root: python tests/make_fixtures.py
Uses the main skill's builder and the fictional 'Sample Client' plan, fills realistic check-in data,
and (if LibreOffice is installed) recalculates so the files carry cached values like a Google Sheets
download does.
"""
from __future__ import annotations

import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parent.parent
MAIN = ROOT / "skills" / "fitness-lifestyle-coach"
OUT = ROOT / "tests" / "fixtures"
SOFFICE = shutil.which("soffice") or shutil.which("libreoffice")
REFLECTION_KEYS = ["got_in_way", "did_about_it", "stress", "feeling", "win"]


def build(tmp: Path) -> tuple[Path, Path]:
    subprocess.run([sys.executable, MAIN / "scripts" / "build_workbook.py", MAIN / "assets" / "example-plan.json",
                    "--out-dir", tmp], check=True, capture_output=True)
    coach = next(tmp.glob("*(Coach).xlsx"))
    client = next(p for p in tmp.glob("*.xlsx") if "(Coach)" not in p.name)
    return coach, client


def blocks(ws):
    """Yield (header_row, first_day_row, this_week_row, reflection_rows, coach_rows) per week."""
    r = 1
    while r <= ws.max_row:
        if ws.cell(r, 1).value == "Date":
            d0 = r + 1
            tw = d0
            while ws.cell(tw, 1).value != "This week":
                tw += 1
            refl = list(range(tw + 1, tw + 6))
            coach = list(range(tw + 6, tw + 9))
            yield r, d0, tw, refl, coach
            r = tw + 9
        else:
            r += 1


def fill_week(ws, blk, days, reflection=None, coach=None):
    hdr, d0, tw, refl, coach_rows = blk
    cols = {str(ws.cell(hdr, c).value).split("\n")[0]: c for c in range(1, ws.max_column + 1) if ws.cell(hdr, c).value}
    for i, day in enumerate(days):
        for key, val in day.items():
            ws.cell(d0 + i, cols[key]).value = val
    if reflection:
        for row, key in zip(refl, REFLECTION_KEYS):
            if reflection.get(key):
                ws.cell(row, 4).value = reflection[key]
    if coach:
        for row, val in zip(coach_rows, coach):
            if val:
                ws.cell(row, 4).value = val


def day(done, weight, steps, sleep, nut, hyd, energy, off="", symptoms="", notes=""):
    d = {"Session done": done, "Morning weight": weight, "Steps": steps, "Sleep": sleep,
         "Nutrition on plan": nut, "Hydration": hyd, "Energy": energy}
    if off:
        d["Off-plan meals"] = off
    if symptoms:
        d["Pain / symptoms"] = symptoms
    if notes:
        d["Notes"] = notes
    return d


def measurements(ws, values_by_site):
    for r in range(1, ws.max_row + 1):
        site = ws.cell(r, 1).value
        if site in values_by_site and ws.cell(r, 3).data_type != "f":
            for i, v in enumerate(values_by_site[site]):
                ws.cell(r, 3 + i).value = v
            values_by_site = {k: v for k, v in values_by_site.items() if k != site}


def recalc_into(path: Path, dest: Path):
    if not SOFFICE:
        shutil.copy(path, dest)
        return
    with tempfile.TemporaryDirectory() as t:
        subprocess.run([SOFFICE, "--headless", "--calc", "--convert-to", "xlsx:Calc MS Excel 2007 XML",
                        "--outdir", t, str(path)], capture_output=True, timeout=240)
        shutil.copy(Path(t) / path.name, dest)


def weeks_1_to_3(ws, red_flag=False):
    bl = list(blocks(ws))
    w1 = [day("Y", 72.6, 8100, 7, 4, 4, 4), day("Y", 72.5, 9200, 7, 4, 3, 4), day("Y", 72.4, 8800, 6.5, 4, 4, 3),
          day("Y", 72.5, 9000, 7, 5, 4, 4), day("", 72.3, 7600, 7, 4, 4, 4), day("Y", 72.2, 10200, 7.5, 3, 3, 4,
          off="Pizza with friends, 3 slices"), day("", 72.4, 6000, 8, 4, 4, 5)]
    w2 = [day("Y", 72.2, 8500, 7, 4, 4, 4), day("Y", 72.1, 9400, 7, 4, 4, 4),
          day("Y", 72.0, 8000, 6.5, 4, 3, 3, symptoms="Left knee 3/10 on squat to chair, fine next morning"),
          day("Y", 72.1, 9100, 7, 4, 4, 4), day("Busy", 71.9, 7000, 6, 3, 3, 3), day("N", 72.0, 5200, 7, 3, 3, 3,
          off="Wedding dinner — biryani and 2 sweets"), day("", 72.1, 6500, 8, 4, 4, 4)]
    if red_flag:
        w3 = [day("Y", 72.0, 8300, 6, 4, 4, 3), day("N", 72.1, 6100, 5.5, 3, 3, 2),
              day("Y", 72.2, 7400, 6, 3, 3, 2, symptoms="Chest pressure and felt dizzy during squats, sat down 10 min, then OK"),
              day("Y", 72.0, 7900, 6, 3, 3, 3, notes="Did the workout, felt a bit tight in the chest again on the last set"),
              day("N", 72.1, 5000, 6, 3, 3, 2), day("N", 72.3, 4800, 7, 3, 3, 3), day("", 72.2, 5200, 7, 3, 3, 3)]
        refl3 = {"got_in_way": "Audit at work, very long days", "did_about_it": "Tried to keep the walks",
                 "stress": "High, audit + bad sleep", "feeling": "Tired. The chest thing scared me a bit but it went away.",
                 "win": "Didn't skip breakfast once"}
    else:
        w3 = [day("Y", 72.1, 8200, 6, 3, 3, 3), day("N", 72.2, 6100, 5.5, 3, 3, 2,
              off="Ordered biryani at office, 1 plate"), day("N", 72.3, 5900, 5.5, 2, 2, 2,
              off="Pav bhaji dinner, worked till 11"), day("Y", 72.1, 7800, 6, 3, 3, 3,
              symptoms="Left knee 3/10 on squat to chair again, settled by evening"), day("N", 72.2, 5000, 6, 3, 3, 2,
              off="Ordered pizza, 4 slices"), day("N", 72.0, 6400, 7.5, 4, 4, 3), day("", 72.2, 7000, 8, 4, 4, 4)]
        refl3 = {"got_in_way": "Audit at work — 12-hour days, ordered food three times, felt guilty",
                 "did_about_it": "Did my after-dinner walks most days",
                 "stress": "High this week, should calm down after the audit ends on the 3rd",
                 "feeling": "Annoyed with myself, but I still want to keep going",
                 "win": "Walked after dinner 6 out of 7 days"}
    fill_week(ws, bl[0], w1, {"got_in_way": "Nothing much", "did_about_it": "-", "stress": "Low",
                              "feeling": "Excited, the workouts are doable", "win": "Did all 3 workouts"},
              coach=["Great first week!", "Add the Friday session from week 3", ""])
    fill_week(ws, bl[1], w2, {"got_in_way": "Cousin's wedding on Saturday", "did_about_it": "Used the Busy Day workout",
                              "stress": "Medium", "feeling": "Good, a bit sore", "win": "Squats feel easier"},
              coach=["Nice use of the Busy Day session.", "Keep the same plan", ""])
    fill_week(ws, bl[2], w3, refl3)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        coach, client = build(tmp)
        shutil.copy(coach, OUT / "sample-client-coach-copy.xlsx")
        for name, red in (("checkin-week3-client.xlsx", False), ("checkin-week3-redflag-client.xlsx", True)):
            wb = load_workbook(client)
            weeks_1_to_3(wb["Check-in Tracker"], red_flag=red)
            measurements(wb["Measurements"], {"Body weight (avg of 3 mornings)": [72.5, 72.0],
                                             "Waist (at navel)": [92, 90.5]})
            p = tmp / name
            wb.save(p)
            recalc_into(p, OUT / name)
        # week 4 live sheet for a mid-block update
        wb = load_workbook(client)
        weeks_1_to_3(wb["Check-in Tracker"])
        p = tmp / "sample-client-week4-client.xlsx"
        wb.save(p)
        recalc_into(p, OUT / p.name)
        # full 12 weeks for a re-plan
        random.seed(7)
        wb = load_workbook(client)
        ws = wb["Check-in Tracker"]
        bl = list(blocks(ws))
        weight = 72.6
        for w, blk in enumerate(bl):
            days = []
            for d in range(7):
                weight -= 0.04 + random.uniform(-0.05, 0.05)
                done = random.choices(["Y", "N", "Busy", ""], [0.62, 0.12, 0.08, 0.18])[0]
                days.append(day(done, round(weight + random.uniform(-0.3, 0.3), 1), random.randint(6500, 10500),
                                round(random.uniform(6, 8), 1), random.randint(3, 5), random.randint(3, 5),
                                random.randint(3, 5)))
            fill_week(ws, blk, days, {"got_in_way": "Work" if w % 3 == 0 else "Nothing major",
                                      "feeling": "Good", "win": f"Week {w + 1} done"})
        measurements(wb["Measurements"], {"Body weight (avg of 3 mornings)": [72.5, 71.8, 71.0, 70.4, 69.9, 69.5, 69.1],
                                         "Waist (at navel)": [92, 91, 90, 89, 88, 87, 86]})
        p = tmp / "sample-client-12wk-client.xlsx"
        wb.save(p)
        recalc_into(p, OUT / p.name)
    for f in sorted(OUT.glob("*.xlsx")):
        print(f.relative_to(ROOT))


if __name__ == "__main__":
    main()
