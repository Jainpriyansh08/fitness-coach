#!/usr/bin/env python3
"""Build a client coaching workbook (.xlsx) from a plan JSON file.

Usage:
    python build_workbook.py plan.json --out-dir OUT [--brand brand.json] [--copy both|coach|client]

Produces up to two files:
    <Client> - <Title> vX (Coach).xlsx  every tab, including Coach Notes, Evidence & Sources,
                                        Decision Log and a hidden _plan_data tab (the plan JSON,
                                        so the plan can be re-read and rebuilt later)
    <Client> - <Title> vX.xlsx          client copy: no coach-only tabs, no hidden data

The workbook uses only functions that work in both Microsoft Excel and Google Sheets
(IF, INT, MIN, MAX, SUM, AVERAGE, COUNT, COUNTA, COUNTIF(S), IFERROR, INDEX, MATCH, LOOKUP,
TEXT, ROUND, TODAY), so it can be uploaded to Google Drive and opened as a Google Sheet.

See ../references/workbook-spec.md for the plan JSON schema.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import math
import re
import sys
import urllib.parse
from pathlib import Path

from openpyxl import Workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

# --------------------------------------------------------------------------------------
# Defaults
# --------------------------------------------------------------------------------------
DEFAULT_BRAND = {
    "coach_name": "",
    "business_name": "",
    "tagline": "",
    "contact": {},
    "checkin_instructions": [],
    "logo_path": "",
    "font": "Arial",
    "colors": {
        "primary": "2F5D50",
        "text": "2B2B2B",
        "muted": "6B6B6B",
        "info_bg": "F6F3EE",
        "input_bg": "FFF4D6",
        "calc_bg": "E8F0EE",
        "home": "A85A45",
        "home_light": "C98A78",
        "gym": "3E5C76",
        "gym_light": "6F8BA3",
        "neutral": "2F5D50",
        "neutral_light": "5E8A7D",
        "coach": "5E5E5E",
        "coach_light": "8A8A8A",
        "link": "1F5FA8",
        "alert_bg": "FBE3DF",
        "good_bg": "DFF0E3",
        "example": "8A8A8A",
    },
}

DEFAULT_MEASUREMENT_SITES = [
    {"site": "Body weight (avg of 3 mornings)", "unit": "kg", "landmark": "Same scale, morning, after the bathroom"},
    {"site": "Waist (at navel)", "unit": "length", "landmark": "Level with the belly button"},
    {"site": "Lower abdomen (5 cm / 2 in below navel)", "unit": "length", "landmark": "Two fingers' width below the belly button"},
    {"site": "Hips / glutes (widest point)", "unit": "length", "landmark": "Widest part of the buttocks, feet together"},
    {"site": "Chest (nipple line)", "unit": "length", "landmark": "Across the nipples, arms relaxed"},
    {"site": "Upper arm — left (midpoint)", "unit": "length", "landmark": "Halfway between shoulder tip and elbow, arm relaxed"},
    {"site": "Upper arm — right (midpoint)", "unit": "length", "landmark": "Halfway between shoulder tip and elbow, arm relaxed"},
    {"site": "Thigh — left (midpoint)", "unit": "length", "landmark": "Halfway between hip crease and top of the kneecap"},
    {"site": "Thigh — right (midpoint)", "unit": "length", "landmark": "Halfway between hip crease and top of the kneecap"},
    {"site": "Calf — left (widest)", "unit": "length", "landmark": "Widest part, standing with weight on both feet"},
    {"site": "Calf — right (widest)", "unit": "length", "landmark": "Widest part, standing with weight on both feet"},
]

DEFAULT_MEASUREMENT_GUIDE = [
    "Measure on the same morning each time: after the bathroom, before food or water, before training.",
    "Stand relaxed, feet together, arms by your sides. Breathe out normally and measure at the end of the breath — don't suck in.",
    "Tape flat and level all the way round, snug on the skin but not pressing in. Use the same soft tape every time.",
    "Use the same landmarks every time (listed next to each site). Measure each site twice and write the average.",
    "Most tapes show centimetres on one side and inches on the other. Pick one side, choose it in the box below, and use it every time — the sheet converts to the other unit for you.",
    "Body weight: weigh 3 mornings in the check-in week and write the average here — single weigh-ins jump with water and food.",
    "Measurements are optional. Skip any you'd rather not take; strength, energy and consistency count just as much.",
]

# key: (header, width, kind)  kind: yn | input | scale | text
DAILY_FIELDS = {
    "session_done": ("Session done\n(Y / N / Busy / Sick)", 11, "yn"),
    "weight": ("Morning weight\n({w})", 10, "input"),
    "steps": ("Steps", 9, "input"),
    "sleep_hours": ("Sleep\n(hours)", 8, "input"),
    "sleep_quality": ("Sleep quality\n(1–5)", 9, "scale"),
    "nutrition": ("Nutrition on plan\n(1–5)", 10, "scale"),
    "protein": ("Protein\n(g, approx.)", 9, "input"),
    "calories": ("Calories\n(approx.)", 9, "input"),
    "water": ("Water\n(litres)", 8, "input"),
    "hydration": ("Hydration\n(1–5)", 9, "scale"),
    "energy": ("Energy\n(1–5)", 8, "scale"),
    "stress": ("Stress\n(1–5)", 8, "scale"),
    "off_plan": ("Off-plan meals\n(what, how much)", 24, "text"),
    "symptoms": ("Pain / symptoms\n(where, how bad)", 22, "text"),
    "notes": ("Notes", 24, "text"),
}
DEFAULT_DAILY = ["session_done", "weight", "steps", "sleep_hours", "nutrition", "hydration",
                 "energy", "off_plan", "symptoms", "notes"]
# Daily fields that get a weekly average in the Weekly Summary (in this order)
AVG_FIELDS = [("weight", "Avg weight ({w})"), ("steps", "Avg steps"), ("sleep_hours", "Avg sleep (h)"),
              ("sleep_quality", "Avg sleep quality"), ("nutrition", "Avg nutrition (1–5)"),
              ("protein", "Avg protein (g)"), ("calories", "Avg calories"), ("water", "Avg water (L)"),
              ("hydration", "Avg hydration (1–5)"), ("energy", "Avg energy (1–5)"), ("stress", "Avg stress (1–5)")]

DEFAULT_REFLECTION = [
    "What got in the way this week?",
    "What did you do about it?",
    "Anything stressful going on that you'd like to talk about?",
    "How are you feeling about the process overall?",
    "One win you're proud of (it doesn't have to be fitness)",
]
COACH_ROWS = ["Coach notes", "Changes for next week", "Coach video / voice note (link)"]

TAB = {
    "overview": "Overview",
    "progression": "Progression",
    "nutrition": "Nutrition",
    "supplements": "Supplements & Remedies",
    "lifestyle": "Lifestyle & Recovery",
    "checkin": "Check-in Tracker",
    "summary": "Weekly Summary",
    "measurements": "Measurements",
    "reviews": "Progress Reviews",
    "changelog": "Change Log",
    "coach": "Coach Notes",
    "evidence": "Evidence & Sources",
    "decisions": "Decision Log",
    "data": "_plan_data",
}
COACH_ONLY = {TAB["coach"], TAB["evidence"], TAB["decisions"], TAB["data"]}


def q(sheet: str) -> str:
    return "'" + sheet.replace("'", "''") + "'"


def safe_tab(name: str) -> str:
    name = re.sub(r"[\[\]\*\?/\\:]", "-", str(name)).strip()
    return name[:31]


def parse_date(s):
    if not s:
        return None
    if isinstance(s, (dt.date, dt.datetime)):
        return s
    return dt.datetime.strptime(str(s)[:10], "%Y-%m-%d")


def deep_merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if k.startswith("_"):
            continue
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def normalise_length_unit(u):
    u = str(u or "cm").strip().lower()
    return "in" if u in ("in", "inch", "inches", '"') else "cm"


def spans_to_starts(spans):
    starts, c = [], 1
    for s in spans:
        starts.append(c)
        c += s
    return starts


# --------------------------------------------------------------------------------------
# Styling helpers
# --------------------------------------------------------------------------------------
class Style:
    def __init__(self, brand: dict):
        self.c = brand["colors"]
        self.fontname = brand.get("font", "Arial")
        thin = Side(style="thin", color="D9D4CC")
        self.border = Border(left=thin, right=thin, top=thin, bottom=thin)

    def font(self, color=None, bold=False, size=10, italic=False, underline=None):
        return Font(name=self.fontname, color="FF" + (color or self.c["text"]), bold=bold,
                    size=size, italic=italic, underline=underline)

    def fill(self, key_or_hex):
        hexv = self.c.get(key_or_hex, key_or_hex)
        return PatternFill("solid", fgColor="FF" + hexv)

    def cf(self, key_or_hex):
        """Fill for conditional formatting (needs start and end colour set)."""
        hexv = "FF" + self.c.get(key_or_hex, key_or_hex)
        return PatternFill(start_color=hexv, end_color=hexv, fill_type="solid")


WRAP_TOP = Alignment(wrap_text=True, vertical="top")
WRAP_CENTER = Alignment(wrap_text=True, vertical="center", horizontal="center")
WRAP_LEFT_CENTER = Alignment(wrap_text=True, vertical="center")


class Sheet:
    """Thin wrapper that tracks the current row and column widths for height estimates."""

    def __init__(self, wb: Workbook, title: str, st: Style, ncols: int, widths: list[float]):
        self.ws = wb.create_sheet(safe_tab(title))
        self.title = self.ws.title
        self.st = st
        self.ncols = ncols
        self.widths = widths + [12] * max(0, ncols - len(widths))
        for i, w in enumerate(self.widths[:ncols], start=1):
            self.ws.column_dimensions[get_column_letter(i)].width = w
        self.row = 2
        self.ws.sheet_view.showGridLines = False
        ps = self.ws.page_setup
        ps.orientation = "landscape"
        ps.fitToWidth = 1
        ps.fitToHeight = 0
        self.ws.sheet_properties.pageSetUpPr.fitToPage = True

    # ---- low level
    def cell(self, r, c, value=None, font=None, fill=None, align=WRAP_TOP, border=False, fmt=None):
        cell = self.ws.cell(row=r, column=c)
        if value is not None:
            cell.value = value
        cell.font = font if font is not None else self.st.font()
        if fill is not None:
            cell.fill = fill
        cell.alignment = align
        if border:
            cell.border = self.st.border
        if fmt:
            cell.number_format = fmt
        return cell

    def merge(self, r, c1, c2, r2=None):
        r2 = r2 or r
        if c2 > c1 or r2 > r:
            self.ws.merge_cells(start_row=r, start_column=c1, end_row=r2, end_column=c2)

    def span_width(self, c1, c2):
        return sum(self.widths[c1 - 1:c2])

    def fit_height(self, r, texts_spans, min_h=15, line_h=12.75):
        """texts_spans: list of (text, width_in_chars)."""
        lines = 1
        for text, width in texts_spans:
            if text is None or isinstance(text, (list, tuple)):
                continue
            s = str(text)
            if s.startswith("="):
                continue
            per_line = max(4.0, width * (1.0 if width < 16 else 1.1))
            n = sum(max(1, math.ceil(len(p) / per_line)) for p in s.split("\n"))
            lines = max(lines, n)
        h = max(min_h, lines * line_h + 4)
        cur = self.ws.row_dimensions[r].height or 0
        self.ws.row_dimensions[r].height = max(h, cur)

    # ---- blocks
    def title_block(self, title, subtitle=None):
        self.cell(2, 1, title, font=self.st.font(self.st.c["primary"], True, 17))
        self.merge(2, 1, self.ncols)
        self.ws.row_dimensions[2].height = 26
        if subtitle:
            self.cell(3, 1, subtitle, font=self.st.font(self.st.c["muted"], size=10))
            self.merge(3, 1, self.ncols)
            self.fit_height(3, [(subtitle, self.span_width(1, self.ncols))])
        self.row = 5

    def band(self, text, color="neutral", size=11, gap_before=True, row=None):
        if row is None:
            if gap_before and self.row > 5:
                self.row += 1
            r = self.row
        else:
            r = row
        for c in range(1, self.ncols + 1):
            self.cell(r, c, fill=self.st.fill(color))
        self.cell(r, 1, text, font=self.st.font("FFFFFF", True, size), fill=self.st.fill(color),
                  align=WRAP_LEFT_CENTER)
        self.merge(r, 1, self.ncols)
        self.ws.row_dimensions[r].height = 20
        self.row = r + 1
        return r

    def heading(self, text):
        if self.row > 5:
            self.row += 1
        self.cell(self.row, 1, text, font=self.st.font(self.st.c["primary"], True, 12))
        self.merge(self.row, 1, self.ncols)
        self.ws.row_dimensions[self.row].height = 18
        self.row += 1

    def kv(self, pairs, label_cols=1):
        for label, value in pairs:
            r = self.row
            for c in range(1, self.ncols + 1):
                self.cell(r, c, fill=self.st.fill("info_bg"), border=True)
            self.cell(r, 1, label, font=self.st.font(self.st.c["primary"], True),
                      fill=self.st.fill("info_bg"), border=True)
            self.merge(r, 1, label_cols)
            self.cell(r, label_cols + 1, value, fill=self.st.fill("info_bg"), border=True)
            self.merge(r, label_cols + 1, self.ncols)
            self.fit_height(r, [(value, self.span_width(label_cols + 1, self.ncols)),
                                (label, self.span_width(1, label_cols))])
            self.row += 1

    def bullets(self, items, prefix="• "):
        for it in items:
            r = self.row
            s = str(it)
            text = s if s.startswith(("•", "✔", "✖", "→")) or re.match(r"^\d+[.)]", s) or not prefix \
                else prefix + s
            self.cell(r, 1, text)
            self.merge(r, 1, self.ncols)
            self.fit_height(r, [(text, self.span_width(1, self.ncols))])
            self.row += 1

    def note(self, text, italic=True, color=None):
        r = self.row
        self.cell(r, 1, text, font=self.st.font(color or self.st.c["muted"], italic=italic))
        self.merge(r, 1, self.ncols)
        self.fit_height(r, [(text, self.span_width(1, self.ncols))])
        self.row += 1

    def table(self, headers, rows, header_color="neutral", spans=None, input_cols=(),
              calc_cols=(), bold_first=True, link_cols=(), fmt=None, height_min=15):
        """spans: column span per header (default 1 each). Returns (first_data_row, last_data_row)."""
        spans = spans or [1] * len(headers)
        starts = spans_to_starts(spans)
        r = self.row
        for i, h in enumerate(headers):
            c1, c2 = starts[i], starts[i] + spans[i] - 1
            for cc in range(c1, c2 + 1):
                self.cell(r, cc, fill=self.st.fill(header_color), border=True)
            self.cell(r, c1, h, font=self.st.font("FFFFFF", True), fill=self.st.fill(header_color),
                      align=WRAP_CENTER if i else WRAP_LEFT_CENTER, border=True)
            self.merge(r, c1, c2)
        self.fit_height(r, [(h, self.span_width(starts[i], starts[i] + spans[i] - 1))
                            for i, h in enumerate(headers)], min_h=18)
        r += 1
        first = r
        for row in rows:
            texts = []
            for i, val in enumerate(row):
                if i >= len(headers):
                    break
                c1, c2 = starts[i], starts[i] + spans[i] - 1
                fill = None
                if i in input_cols:
                    fill = self.st.fill("input_bg")
                elif i in calc_cols:
                    fill = self.st.fill("calc_bg")
                font = self.st.font(bold=(i == 0 and bold_first))
                link = None
                if i in link_cols and isinstance(val, (list, tuple)):
                    val, link = val
                if link:
                    font = self.st.font(self.st.c["link"], True, underline="single")
                for cc in range(c1, c2 + 1):
                    self.cell(r, cc, fill=fill, border=True)
                cell = self.cell(r, c1, val, font=font, fill=fill, border=True, fmt=(fmt or {}).get(i))
                if link:
                    cell.hyperlink = link
                self.merge(r, c1, c2)
                texts.append((val, self.span_width(c1, c2)))
            self.fit_height(r, texts, min_h=height_min)
            r += 1
        self.row = r
        return first, r - 1


# --------------------------------------------------------------------------------------
# Layout shared by the builder and the pre-computed references
# --------------------------------------------------------------------------------------
def daily_fields_of(plan):
    tr = plan.get("tracking", {})
    return [f for f in tr.get("daily_fields", DEFAULT_DAILY) if f in DAILY_FIELDS]


def summary_columns(fields, units):
    """Weekly Summary columns: list of (key, header, width)."""
    cols = [("week", "Week", 6), ("starts", "Starts", 10), ("phase", "Phase", 18),
            ("planned", "Sessions planned", 9), ("done", "Sessions done", 9), ("attendance", "Attendance", 10)]
    for k, h in AVG_FIELDS:
        if k in fields:
            cols.append((f"avg_{k}", h.replace("{w}", units["weight"]), 10))
            if k == "weight":
                cols.append(("weight_change", "Change vs last week", 9))
    if "symptoms" in fields:
        cols.append(("symptom_days", "Days with pain / symptoms", 10))
    cols += [("win", "Client's win of the week", 30), ("changes", "Coach: changes for next week", 30)]
    return cols


SUMMARY_FIRST_ROW = 6  # title rows 2-3, header row 5


# --------------------------------------------------------------------------------------
# Builder
# --------------------------------------------------------------------------------------
def sanitise(obj):
    """Plan text must never become a formula: prefix a space to strings starting with '='."""
    if isinstance(obj, dict):
        return {k: sanitise(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitise(v) for v in obj]
    if isinstance(obj, str) and obj.startswith("="):
        return " " + obj
    return obj


class Builder:
    def __init__(self, plan: dict, brand: dict, client_copy: bool):
        self.original_plan = plan
        plan = sanitise(plan)
        self.p = plan
        self.brand = brand
        self.client_copy = client_copy
        self.st = Style(brand)
        self.wb = Workbook()
        self.wb.remove(self.wb.active)
        self.ref: dict[str, str] = {}
        self.built_tabs: list[tuple[str, str]] = []  # (tab, purpose) in order
        meta = plan["meta"]
        self.start = parse_date(meta["start_date"])
        self.days = int(meta.get("days") or int(meta.get("weeks", 4)) * 7)
        self.weeks = math.ceil(self.days / 7)
        self.first_week = int(meta.get("first_week_number", 1))
        self.units = {"weight": "kg", "length": "cm", **meta.get("units", {})}
        self.fields = daily_fields_of(plan)
        self.scols = summary_columns(self.fields, self.units)
        self.scol = {k: get_column_letter(i + 1) for i, (k, _, _) in enumerate(self.scols)}

    # ---------------- helpers
    def video_cell(self, ex):
        url = ex.get("video")
        if url:
            return ("▶ Watch", url)
        name = ex.get("name") or ""
        if not name:
            return ""
        query = urllib.parse.quote_plus(f"{name} exercise proper form")
        return ("▶ Find a demo", f"https://www.youtube.com/results?search_query={query}")

    def add_tab_purpose(self, tab, purpose):
        self.built_tabs.append((tab, purpose))

    def srange(self, key):
        L = self.scol[key]
        return f"{q(TAB['summary'])}!${L}${SUMMARY_FIRST_ROW}:${L}${SUMMARY_FIRST_ROW + self.weeks - 1}"

    # ---------------- Overview (created first so it is the first tab)
    def create_overview(self):
        self.ov = Sheet(self.wb, TAB["overview"], self.st, 8, [24, 24, 22, 16, 16, 16, 18, 16])
        self.ov.ws.freeze_panes = "A5"

    def fill_overview(self):
        o = self.p.get("overview", {})
        meta = self.p["meta"]
        sh, st, b = self.ov, self.st, self.brand
        sh.title_block(f'{meta["client_name"]} — {meta["plan_title"]}', meta.get("subtitle"))
        brand_bits = [x for x in [b.get("business_name"), b.get("coach_name") and f'Coach: {b["coach_name"]}',
                                  b.get("tagline")] if x]
        if brand_bits:
            sh.cell(4, 1, " · ".join(brand_bits), font=st.font(st.c["primary"], italic=True, size=9))
            sh.merge(4, 1, sh.ncols)
        sh.row = 5
        sh.band("Plan dashboard", "neutral", gap_before=False)
        r0 = sh.row  # = 6
        rows = [
            ("Plan starts (Day 1)", self.start, "input", "dd mmm yyyy"),
            ("Plan ends", f"=C{r0}+{self.days - 1}", "calc", "dd mmm yyyy"),
            ("Target date / event", parse_date(meta.get("target_date")) or "—", "input", "dd mmm yyyy"),
            ("Today", "=TODAY()", "calc", "dd mmm yyyy"),
            ("Current week",
             f'=IF(C{r0 + 3}<C{r0},"Not started",IF(C{r0 + 3}>C{r0 + 1},"Complete",'
             f'INT((C{r0 + 3}-C{r0})/7)+{self.first_week}))', "calc", None),
        ]
        if self.ref.get("phase_starts"):
            rows.append(("Current phase",
                         f'=IF(ISNUMBER(C{r0 + 4}),LOOKUP(C{r0 + 4}-{self.first_week - 1},'
                         f'{self.ref["phase_starts"]},{self.ref["phase_names"]}),C{r0 + 4})', "calc", None))
        rows.append(("Days to target", f'=IF(ISNUMBER(C{r0 + 2}),MAX(0,C{r0 + 2}-C{r0 + 3}),"—")', "calc", None))
        if "weight" in self.fields:
            rows.append((f"Starting weight ({self.units['weight']})", meta.get("starting_weight") or "", "input", "0.0"))
            sw = r0 + len(rows) - 1
            wr = self.srange("avg_weight")
            rows.append(("Latest weekly average weight", f'=IFERROR(INDEX({wr},MATCH(9.99E+307,{wr})),"—")',
                         "calc", "0.0"))
            rows.append(("Change since start", f'=IFERROR(C{sw + 1}-C{sw},"—")', "calc", "+0.0;-0.0;0.0"))
        rows.append(("Sessions done so far", f'=SUM({self.srange("done")})', "calc", None))
        rows.append(("Average attendance (logged weeks)",
                     f'=IFERROR(AVERAGE({self.srange("attendance")}),"No weeks logged yet")', "calc", "0%"))
        for k, label in (("avg_energy", "Average energy (1–5)"), ("avg_sleep_hours", "Average sleep (hours)")):
            if k in self.scol:
                rows.append((label, f'=IFERROR(ROUND(AVERAGE({self.srange(k)}),1),"—")', "calc", None))
        for i, (label, val, kind, fmt) in enumerate(rows):
            r = r0 + i
            sh.cell(r, 1, label, font=st.font(st.c["primary"], True), fill=st.fill("info_bg"), border=True)
            sh.cell(r, 2, fill=st.fill("info_bg"), border=True)
            sh.merge(r, 1, 2)
            bg = st.fill("input_bg" if kind == "input" else "calc_bg")
            sh.cell(r, 3, val, fill=bg, border=True, font=st.font(bold=True), fmt=fmt, align=WRAP_LEFT_CENTER)
            sh.cell(r, 4, fill=bg, border=True)
            sh.merge(r, 3, 4)
        self.ref["start"] = f"{q(TAB['overview'])}!$C${r0}"
        key = [("Yellow cell", "You fill this in", "input_bg"), ("Green-grey cell", "Calculates itself", "calc_bg"),
               ("Terracotta band", "Home version", "home"), ("Slate band", "Gym version", "gym"),
               ("Grey band", "Your coach writes here", "coach")]
        sh.cell(r0, 6, "Colour key", font=st.font(st.c["primary"], True))
        for i, (a, desc, col) in enumerate(key):
            sh.cell(r0 + 1 + i, 6, a, fill=st.fill(col),
                    font=st.font("FFFFFF" if col in ("home", "gym", "coach") else None, True), border=True)
            sh.cell(r0 + 1 + i, 7, desc, border=True)
            sh.cell(r0 + 1 + i, 8, border=True)
            sh.merge(r0 + 1 + i, 7, 8)
        sh.row = r0 + max(len(rows), len(key) + 1)

        sched = o.get("schedule")
        if sched:
            sh.band(o.get("schedule_title", "Your week"), "neutral")
            phase_cols = o.get("phase_columns", [])[:4]
            headers = ["Day", "Session", "Where to find it", "Time"] + phase_cols
            rows_ = [[s.get("day", ""), s.get("session", ""), s.get("tab", "—"), s.get("time", "")] +
                     [s.get("phases", {}).get(pc, "") for pc in phase_cols] for s in sched]
            spans = [1] * len(headers)
            spans[1] += sh.ncols - len(headers)
            first, last = sh.table(headers, rows_, spans=spans)
            self.ref["sched_day"] = f"{q(TAB['overview'])}!$A${first}:$A${last}"
            self.ref["sched_session"] = f"{q(TAB['overview'])}!$B${first}:$B${last}"
            if o.get("schedule_note"):
                sh.note(o["schedule_note"])
        for title, k, color in (("The few things that matter most", "priorities", "neutral"),
                                ("What to expect", "expectations", "neutral"),
                                ("Listen to your body", "listen_to_body", "home")):
            if o.get(k):
                sh.band(o.get(k + "_title", title), color)
                sh.bullets(o[k])
        if o.get("equipment"):
            sh.band("What you need", "neutral")
            sh.bullets([o["equipment"]], prefix="")
        ci = o.get("checkin_instructions") or b.get("checkin_instructions")
        contact = {k: v for k, v in (b.get("contact") or {}).items() if v}
        if ci or contact:
            sh.band("How check-ins work", "neutral")
            if ci:
                sh.bullets(ci)
            if contact:
                sh.kv([(k.replace("_", " ").title(), v) for k, v in contact.items()], label_cols=2)
        sh.band("Workbook tabs", "neutral")
        self.tab_guide_row = sh.row
        logo = b.get("logo_path")
        if logo and Path(logo).exists():
            try:
                from openpyxl.drawing.image import Image as XLImage
                img = XLImage(logo)
                ratio = 48 / max(1, img.height)
                img.height = 48
                img.width = int(img.width * ratio)
                sh.ws.add_image(img, "H1")
            except Exception as e:  # pragma: no cover
                print(f"warning: logo not added ({e})", file=sys.stderr)

    def write_tab_guide(self):
        seen, rows = set(), []
        for t, p in self.built_tabs:
            if t in seen or t == TAB["data"] or (self.client_copy and t in COACH_ONLY):
                continue
            seen.add(t)
            rows.append([t, p])
        self.ov.row = self.tab_guide_row
        self.ov.table(["Tab", "What it's for"], rows, spans=[2, 6])

    # ---------------- Session tabs (workouts, mobility, busy day)
    EX_FIELDS = [
        ("pattern", "Pattern", 13), ("name", "Exercise", 24), ("cues", "How to do it (key cues)", 44),
        ("_presc", None, 13), ("rest", "Rest", 9), ("effort", "Effort", 12), ("easier", "Easier option", 24),
        ("harder", "Harder — only when ready", 26), ("if_bothers", "If it bothers you", 26),
        ("video", "Video demo", 13),
    ]

    def build_session(self, s):
        blocks = s.get("blocks", [])
        n_presc = max([len(bl.get("prescription_labels", [])) for bl in blocks] + [1])
        present = set()
        for bl in blocks:
            for ex in bl.get("exercises", []):
                present |= {k for k, v in ex.items() if v not in (None, "", [])}
        cols = []
        for key, header, width in self.EX_FIELDS:
            if key == "_presc":
                cols += [(f"_presc{i}", None, 13) for i in range(n_presc)]
            elif key in ("name", "video") or key in present:
                cols.append((key, header, width))
        sh = Sheet(self.wb, s["tab"], self.st, len(cols), [w for _, _, w in cols])
        sh.title_block(s.get("title", s["tab"]), s.get("subtitle"))
        sh.ws.freeze_panes = "A5"
        if s.get("info"):
            sh.kv([tuple(x) for x in s["info"]])
        for bl in blocks:
            style = bl.get("style", "neutral")
            sh.band(bl.get("label", ""), style)
            labels = bl.get("prescription_labels") or ["Sets × reps"]
            headers = []
            for key, header, _ in cols:
                if key.startswith("_presc"):
                    i = int(key[6:])
                    headers.append(labels[i] if i < len(labels) else "")
                else:
                    headers.append(header)
            rows = []
            for ex in bl.get("exercises", []):
                row = []
                for key, _, _ in cols:
                    if key.startswith("_presc"):
                        pres = ex.get("prescription", [])
                        pres = [pres] if isinstance(pres, str) else pres
                        i = int(key[6:])
                        row.append(pres[i] if i < len(pres) else "")
                    elif key == "video":
                        row.append(self.video_cell(ex))
                    else:
                        row.append(ex.get(key, ""))
                rows.append(row)
            light = style + "_light"
            sh.table(headers, rows, header_color=light if light in self.st.c else style,
                     link_cols=(len(cols) - 1,))
            if bl.get("note"):
                sh.note(bl["note"])
        if s.get("footer"):
            sh.row += 1
            sh.note(s["footer"], italic=False, color=self.st.c["primary"])
        if s.get("kind", "workout") == "workout" and s.get("my_notes", True):
            sh.heading("My notes (fill in)")
            qs = s.get("my_notes_questions") or ["Favourite exercise today", "Exercise I'd like to swap",
                                                  "Weight / version I used for the main exercise"]
            sh.table(["Question", "Your answer"], [[x, ""] for x in qs], spans=[2, len(cols) - 2], input_cols=(1,))
        self.add_tab_purpose(sh.title, s.get("purpose", "Your session — exercises, sets, cues and videos"))

    # ---------------- Progression
    def build_progression(self):
        pr = self.p.get("progression")
        if not pr:
            return
        sh = Sheet(self.wb, TAB["progression"], self.st, 7, [26, 10, 10, 22, 30, 32, 26])
        sh.title_block(pr.get("title", "Progression — how the plan builds"), pr.get("subtitle"))
        sh.ws.freeze_panes = "A5"
        phases = pr.get("phases", [])
        if phases:
            sh.band("Phases", "neutral", gap_before=False)
            start = f"{q(TAB['overview'])}!$C$6"
            rows = [[ph["name"], ph["start_week"], ph["end_week"], None, ph.get("sessions", ""),
                     ph.get("aim", ""), ph.get("sets_effort", "")] for ph in phases]
            first, last = sh.table(["Phase", "Start week", "End week", "Dates", "Sessions per week",
                                    "Main aim", "Sets and effort"], rows, calc_cols=(3,))
            for r in range(first, last + 1):
                sh.ws.cell(r, 4).value = (f'=TEXT({start}+7*(B{r}-1),"d mmm")&" – "&'
                                          f'TEXT({start}+7*C{r}-1,"d mmm yyyy")')
            self.ref["phase_starts"] = f"{q(TAB['progression'])}!$B${first}:$B${last}"
            self.ref["phase_names"] = f"{q(TAB['progression'])}!$A${first}:$A${last}"
        for sec in pr.get("sections", []):
            sh.band(sec["title"], sec.get("style", "neutral"))
            if sec.get("bullets"):
                sh.bullets(sec["bullets"], prefix=sec.get("prefix", "• "))
            if sec.get("table"):
                t = sec["table"]
                n = len(t["headers"])
                spans = t.get("spans") or ([1] * (n - 1) + [7 - (n - 1)] if n < 7 else [1] * n)
                sh.table(t["headers"], t["rows"], spans=spans)
        self.add_tab_purpose(sh.title, "How and when exercises get harder; phases and lighter weeks")

    # ---------------- Nutrition (16-column grid; every table uses spans)
    def build_nutrition(self):
        n = self.p.get("nutrition")
        if not n:
            return
        G = 16
        sh = Sheet(self.wb, TAB["nutrition"], self.st, G, [13] + [10] * (G - 1))
        sh.title_block(n.get("title", "Nutrition"), n.get("subtitle"))
        sh.ws.freeze_panes = "A5"
        if n.get("targets"):
            sh.band("Your daily targets · starting estimates, reviewed at check-ins", "neutral", gap_before=False)
            rows = [[t.get("what"), t.get("target"), t.get("low", ""), t.get("high", ""), t.get("why", "")]
                    for t in n["targets"]]
            sh.table(["What", "Target", "Low end", "High end", "Why / how to think about it"], rows,
                     spans=[2, 3, 1, 1, 9])
        if n.get("guides"):
            sh.band("Guides", "neutral")
            sh.kv([tuple(x) for x in n["guides"]], label_cols=2)
        for mp in n.get("meal_plans", []):
            sh.band(mp.get("title", "Meal plan"), mp.get("style", "home"))
            if mp.get("intro"):
                sh.note(mp["intro"], italic=False)
            numeric = [k for k in ("protein", "carbs", "fat", "fibre", "kcal")
                       if any(k in it for m in mp["meals"] for it in m["items"])]
            names = {"protein": "Protein (g)", "carbs": "Carbs (g)", "fat": "Fat (g)", "fibre": "Fibre (g)",
                     "kcal": "kcal"}
            headers = ["Meal", "Time", "Food", "Quantity"] + [names[k] for k in numeric] + \
                      ["Alternative (same slot)", "Notes"]
            spans = [1, 1, 3, 2] + [1] * len(numeric)
            rem = G - sum(spans)
            spans += [math.ceil(rem / 2), rem // 2]
            starts = spans_to_starts(spans)
            rows, counts = [], []
            for m in mp["meals"]:
                for j, it in enumerate(m["items"]):
                    rows.append([m["meal"] if j == 0 else "", m.get("time", "") if j == 0 else "",
                                 it.get("food", ""), it.get("qty", "")] + [it.get(k, "") for k in numeric] +
                                [it.get("alternative", ""), it.get("notes", "")])
                counts.append(len(m["items"]))
            first, last = sh.table(headers, rows, spans=spans)
            r = first
            for cnt in counts:
                if cnt > 1:
                    sh.ws.merge_cells(start_row=r, start_column=1, end_row=r + cnt - 1, end_column=1)
                    sh.ws.merge_cells(start_row=r, start_column=2, end_row=r + cnt - 1, end_column=2)
                r += cnt
            if numeric:
                tr = sh.row
                for c in range(1, G + 1):
                    sh.cell(tr, c, fill=self.st.fill("calc_bg"), border=True)
                sh.cell(tr, 1, "Day total (approx.)", font=self.st.font(self.st.c["primary"], True),
                        fill=self.st.fill("calc_bg"), border=True)
                sh.merge(tr, 1, starts[4] - 1)
                for i in range(len(numeric)):
                    L = get_column_letter(starts[4 + i])
                    sh.cell(tr, starts[4 + i], f"=ROUND(SUM({L}{first}:{L}{last}),0)", font=self.st.font(bold=True),
                            fill=self.st.fill("calc_bg"), border=True)
                sh.row += 1
            if mp.get("note"):
                sh.note(mp["note"])
        menu = n.get("menu")
        if menu:
            sh.band(menu.get("title", "Sample week — rotate days freely and use the swap list"), "home")
            slots = menu.get("slots", ["Breakfast", "Lunch", "Dinner", "Snack"])
            per_slot = max(2, (G - 1 - 1 - 2) // len(slots))
            spans = [1]
            headers = ["Day"]
            for s in slots:
                headers += [s, "Protein (g)"]
                spans += [per_slot - 1, 1]
            headers += ["Day total (g)", "Swaps / alternatives"]
            spans += [1, G - sum(spans) - 1]
            starts = spans_to_starts(spans)
            rows = []
            for d in menu["days"]:
                row = [d["day"]]
                for s in slots:
                    v = d.get(s.lower(), ["", ""])
                    v = [v, ""] if isinstance(v, str) else v
                    row += [v[0], v[1] if len(v) > 1 else ""]
                row += ["", d.get("swaps", "")]
                rows.append(row)
            tot_idx = len(headers) - 2
            first, last = sh.table(headers, rows, spans=spans, calc_cols=(tot_idx,))
            prot_cols = [get_column_letter(starts[2 + 2 * i]) for i in range(len(slots))]
            tot_col = starts[tot_idx]
            for r in range(first, last + 1):
                sh.ws.cell(r, tot_col).value = "=SUM(" + ",".join(f"{c}{r}" for c in prot_cols) + ")"
            tr = sh.row
            sh.cell(tr, tot_col - 1, "Average", font=self.st.font(bold=True))
            L = get_column_letter(tot_col)
            sh.cell(tr, tot_col, f"=ROUND(AVERAGE({L}{first}:{L}{last}),0)", font=self.st.font(bold=True),
                    fill=self.st.fill("calc_bg"), border=True)
            sh.row += 1
            if menu.get("note"):
                sh.note(menu["note"])
        if n.get("timing"):
            sh.band(n.get("timing_title", "Meal timing around training"), "neutral")
            sh.table(["Option", "When", "What to eat", "Notes"],
                     [[t.get("option"), t.get("when"), t.get("what"), t.get("notes", "")] for t in n["timing"]],
                     spans=[1, 3, 9, 3])
        if n.get("swaps"):
            sh.band(n.get("swaps_title", "Swap list — foods with similar protein (approximate)"), "neutral")
            sh.table(["Food", "Portion", "Protein (g)", "kcal (approx.)", "Easy swap"],
                     [[s.get("food"), s.get("portion"), s.get("protein", ""), s.get("kcal", ""), s.get("swap", "")]
                      for s in n["swaps"]], spans=[3, 3, 1, 1, 8])
        for sec in n.get("sections", []):
            sh.band(sec["title"], sec.get("style", "neutral"))
            sh.bullets(sec.get("bullets", []), prefix=sec.get("prefix", "• "))
        self.add_tab_purpose(sh.title, n.get("purpose", "Targets, meals, portions, swaps and eating-out guide"))

    # ---------------- Supplements & remedies
    def build_supplements(self):
        s = self.p.get("supplements")
        if not s:
            return
        sh = Sheet(self.wb, TAB["supplements"], self.st, 8, [22, 12, 30, 13, 28, 36, 24, 16])
        sh.title_block(s.get("title", "Supplements & Remedies"),
                       s.get("subtitle", "Food first. Everything here is optional, chosen for you, and comes with "
                                         "how strong the evidence is and who should be careful."))
        sh.ws.freeze_panes = "A5"
        if s.get("intro"):
            sh.bullets(s["intro"])
        items = s.get("items", [])
        if items:
            sh.band("Your list", "neutral")
            sh.table(["Item", "Type", "Why it's here for you", "Evidence", "How to take it",
                      "Be careful if… / check first", "Alternative", "Status"],
                     [[i.get("name"), i.get("type", "Supplement"), i.get("why_for_you", ""), i.get("evidence", ""),
                       i.get("how", ""), i.get("cautions", ""), i.get("alternative", ""), i.get("status", "")]
                      for i in items])
        if s.get("not_recommended"):
            sh.band("Not recommended for you right now (and why)", "home")
            sh.table(["Item", "Why not"], [[x.get("name"), x.get("why")] for x in s["not_recommended"]],
                     spans=[2, 6])
        sh.band("What the evidence labels mean", "neutral")
        sh.table(["Label", "Meaning"], [
            ["Strong", "Consistent results across several good-quality human trials or meta-analyses."],
            ["Moderate", "Helps in human trials, but the effect is modest or results vary."],
            ["Limited", "Small or short human studies, or mostly lab/animal research. Might help; don't rely on it."],
            ["Traditional", "Long-standing practice with little direct research. Fine to try if it's safe for you; "
                            "expect a small effect at most."],
        ], spans=[2, 6])
        sh.band("Important", "home")
        sh.bullets(s.get("safety_notes") or [
            "Keep taking any prescribed medicine exactly as your doctor advised. Nothing here replaces it.",
            "If you take medicine for blood sugar, blood pressure, thyroid or blood thinning, check with your doctor "
            "or pharmacist before starting any remedy or supplement on this tab.",
            "Stop and tell your coach if anything causes stomach upset, rash, palpitations, dizziness or feeling shaky.",
            "Pregnant, trying to conceive or breastfeeding? Tell your coach — several items change or stop.",
        ])
        self.add_tab_purpose(sh.title, "Optional supplements and home remedies, with evidence and cautions")

    # ---------------- Lifestyle
    def build_lifestyle(self):
        l = self.p.get("lifestyle")
        if not l:
            return
        sh = Sheet(self.wb, TAB["lifestyle"], self.st, 3, [32, 52, 52])
        sh.title_block(l.get("title", "Lifestyle & Recovery"), l.get("subtitle"))
        sh.ws.freeze_panes = "A5"
        if l.get("habits"):
            sh.band(l.get("habits_title", "Your starting habits — just these for now"), "neutral", gap_before=False)
            sh.table(["Habit", "What it looks like", "Why it helps"],
                     [[h["habit"], h.get("what", ""), h.get("why", "")] for h in l["habits"]])
        if l.get("recovery"):
            sh.band("Recovery basics", "neutral")
            sh.table(["Area", "Guidance"], [list(x) for x in l["recovery"]], spans=[1, 2])
        for sec in l.get("sections", []):
            sh.band(sec["title"], sec.get("style", "neutral"))
            sh.bullets(sec.get("bullets", []), prefix=sec.get("prefix", "• "))
        self.add_tab_purpose(sh.title, "A few priority habits, sleep, stress, busy weeks and recovery")

    # ---------------- Check-in tracker: one block per week
    def build_checkin(self):
        tr = self.p.get("tracking", {})
        refl = tr.get("weekly_reflection", DEFAULT_REFLECTION)
        fields = self.fields
        base = [("Date", 11), ("Day", 7), ("Planned session", 26)]
        widths = [w for _, w in base] + [DAILY_FIELDS[f][1] for f in fields]
        ncols = len(widths)
        sh = Sheet(self.wb, TAB["checkin"], self.st, ncols, widths)
        st = self.st
        sh.title_block(
            "Check-in Tracker — 2 minutes each evening, reflection every " + tr.get("checkin_day", "Sunday"),
            tr.get("checkin_intro",
                   "Yellow cells are yours. Session done: Y = done · N = missed · Busy = did the short Busy Day "
                   "version · Sick = unwell · leave it blank on rest days. Ratings: 1 = poor, 5 = great. "
                   "Rough numbers are fine. "
                   "Answer the weekly questions in a sentence or two — your coach replies in the grey rows."))
        sh.ws.freeze_panes = "B1"
        start = self.ref["start"]
        headers = [b for b, _ in base] + [DAILY_FIELDS[f][0].replace("{w}", self.units["weight"]) for f in fields]
        dv_yn = DataValidation(type="list", formula1='"Y,N,Busy,Sick"', allow_blank=True)
        dv_sc = DataValidation(type="whole", operator="between", formula1="1", formula2="5", allow_blank=True)
        dv_sc.error = "Please enter a number from 1 to 5"
        dv_sc.showErrorMessage = True
        sched_mode = self.p.get("overview", {}).get("schedule_mode", "weekday")
        col_of = {f: 4 + j for j, f in enumerate(fields)}
        self.blocks = []
        r = 5
        for w in range(self.weeks):
            wk = self.first_week + w
            ndays = min(7, self.days - 7 * w)
            # band with dates and phase
            phase = ""
            if "phase_starts" in self.ref:
                phase = (f'&IFERROR("   ·   "&LOOKUP({w + 1},{self.ref["phase_starts"]},'
                         f'{self.ref["phase_names"]}),"")')
            band_formula = (f'="WEEK {wk}   ·   "&TEXT({start}+{7 * w},"d mmm")&" – "&'
                            f'TEXT({start}+{7 * w + ndays - 1},"d mmm yyyy"){phase}')
            sh.band(band_formula, "neutral", row=r)
            r += 1
            for i, h in enumerate(headers, start=1):
                sh.cell(r, i, h, font=st.font("FFFFFF", True, 9), fill=st.fill("neutral_light"),
                        align=WRAP_CENTER, border=True)
            sh.ws.row_dimensions[r].height = 30
            r += 1
            d0 = r
            for d in range(ndays):
                rr = d0 + d
                off = 7 * w + d
                sh.cell(rr, 1, f"={start}+{off}", fill=st.fill("calc_bg"), border=True, fmt="dd mmm",
                        font=st.font(size=9))
                sh.cell(rr, 2, f'=TEXT(A{rr},"ddd")', fill=st.fill("calc_bg"), border=True, font=st.font(size=9))
                if "sched_day" in self.ref:
                    if sched_mode == "day_number":
                        f = f'=IFERROR(INDEX({self.ref["sched_session"]},{off + 1}),"")'
                    else:
                        f = (f'=IFERROR(INDEX({self.ref["sched_session"]},MATCH(TEXT(A{rr},"dddd"),'
                             f'{self.ref["sched_day"]},0)),"")')
                else:
                    f = ""
                sh.cell(rr, 3, f, fill=st.fill("calc_bg"), border=True, font=st.font(size=9))
                for fld in fields:
                    sh.cell(rr, col_of[fld], fill=st.fill("input_bg"), border=True, font=st.font(size=9),
                            align=WRAP_TOP if DAILY_FIELDS[fld][2] == "text" else WRAP_CENTER)
                sh.ws.row_dimensions[rr].height = 18
            d1 = d0 + ndays - 1
            # weekly totals row
            ar = d1 + 1
            for c in range(1, ncols + 1):
                sh.cell(ar, c, fill=st.fill("calc_bg"), border=True, font=st.font(bold=True, size=9),
                        align=WRAP_CENTER)
            sh.cell(ar, 1, "This week", fill=st.fill("calc_bg"), border=True,
                    font=st.font(st.c["primary"], True, 9), align=WRAP_LEFT_CENTER)
            sh.merge(ar, 1, 2)
            srow = SUMMARY_FIRST_ROW + w
            sh.cell(ar, 3, f'="Planned: "&{q(TAB["summary"])}!{self.scol["planned"]}{srow}&" sessions"',
                    fill=st.fill("calc_bg"), border=True, font=st.font(st.c["primary"], True, 9),
                    align=WRAP_LEFT_CENTER)
            for fld in fields:
                c = col_of[fld]
                L = get_column_letter(c)
                rng = f"{L}{d0}:{L}{d1}"
                kind = DAILY_FIELDS[fld][2]
                if kind == "yn":
                    v = f'=IF(COUNTA({rng})=0,"",COUNTIF({rng},"Y")+COUNTIF({rng},"Busy"))'
                elif kind in ("input", "scale"):
                    v = f'=IFERROR(ROUND(AVERAGE({rng}),1),"")'
                elif fld == "symptoms":
                    v = (f'=IF(COUNTA({rng})=0,"",IF(COUNTIFS({rng},"<>",{rng},"<>none",{rng},"<>no")=0,'
                         f'"None reported",COUNTIFS({rng},"<>",{rng},"<>none",{rng},"<>no")&" day(s) — coach will review"))')
                elif fld == "off_plan":
                    v = (f'=IF(COUNTIFS({rng},"<>",{rng},"<>none",{rng},"<>no")=0,"",'
                         f'COUNTIFS({rng},"<>",{rng},"<>none",{rng},"<>no")&" off-plan meal(s) logged")')
                else:
                    v = ""
                sh.cell(ar, c, v, fill=st.fill("calc_bg"), border=True, font=st.font(bold=True, size=9),
                        align=WRAP_CENTER, fmt="#,##0" if fld in ("steps", "calories") else None)
            # validation + highlights for this block
            for fld in fields:
                c = col_of[fld]
                L = get_column_letter(c)
                rng = f"{L}{d0}:{L}{d1}"
                kind = DAILY_FIELDS[fld][2]
                if kind == "yn":
                    dv_yn.add(rng)
                elif kind == "scale":
                    dv_sc.add(rng)
                    sh.ws.conditional_formatting.add(
                        rng, FormulaRule(formula=[f"AND(ISNUMBER({L}{d0}),{L}{d0}<=2)"], fill=st.cf("alert_bg")))
                if fld == "symptoms":
                    sh.ws.conditional_formatting.add(
                        rng, FormulaRule(formula=[f'AND({L}{d0}<>"",LOWER({L}{d0})<>"none",LOWER({L}{d0})<>"no")'],
                                         fill=st.cf("alert_bg")))
            r = ar + 1
            # reflection
            q_rows = {}
            for i, question in enumerate(refl):
                for c in range(1, ncols + 1):
                    sh.cell(r, c, fill=st.fill("input_bg"), border=True)
                sh.cell(r, 1, question, font=st.font(st.c["home"], True, 9), fill=st.fill("info_bg"), border=True)
                sh.merge(r, 1, 3)
                sh.cell(r, 4, fill=st.fill("input_bg"), border=True, font=st.font(size=9))
                sh.merge(r, 4, ncols)
                sh.ws.row_dimensions[r].height = 30
                q_rows[i] = r
                r += 1
            c_rows = {}
            for i, label in enumerate(COACH_ROWS):
                for c in range(1, ncols + 1):
                    sh.cell(r, c, fill=st.fill("info_bg"), border=True)
                sh.cell(r, 1, label, font=st.font("FFFFFF", True, 9), fill=st.fill("coach"), border=True,
                        align=WRAP_LEFT_CENTER)
                sh.merge(r, 1, 3)
                sh.cell(r, 4, fill=st.fill("info_bg"), border=True, font=st.font(size=9))
                sh.merge(r, 4, ncols)
                sh.ws.row_dimensions[r].height = 30 if i < 2 else 18
                c_rows[i] = r
                r += 1
            self.blocks.append({"week": wk, "days": (d0, d1), "avg_row": ar, "q_rows": q_rows, "c_rows": c_rows})
            r += 1  # spacer
        sh.ws.add_data_validation(dv_yn)
        sh.ws.add_data_validation(dv_sc)
        self.col_of = col_of
        self.add_tab_purpose(sh.title, "Fill in each evening, plus the weekly questions — your coach replies here")

    # ---------------- Weekly summary (all formulas)
    def build_summary(self):
        tr = self.p.get("tracking", {})
        planned = tr.get("sessions_planned", 3)
        sh = Sheet(self.wb, TAB["summary"], self.st, len(self.scols), [w for _, _, w in self.scols])
        st = self.st
        sh.title_block("Weekly Summary — fills in automatically",
                       "One line per week, pulled from the Check-in Tracker. Use it to spot trends over 2–3 weeks, "
                       "not single days. 'Sessions planned' (yellow) can be edited by the coach.")
        r = 5
        for i, (_, h, _) in enumerate(self.scols, start=1):
            sh.cell(r, i, h, font=st.font("FFFFFF", True, 9), fill=st.fill("neutral"), align=WRAP_CENTER,
                    border=True)
        sh.ws.row_dimensions[r].height = 42
        ct = q(TAB["checkin"])
        start = self.ref["start"]
        win_q = None
        refl = tr.get("weekly_reflection", DEFAULT_REFLECTION)
        for i, qtext in enumerate(refl):
            if "win" in qtext.lower() or "proud" in qtext.lower():
                win_q = i
        win_q = len(refl) - 1 if win_q is None else win_q
        for w, blk in enumerate(self.blocks):
            rr = SUMMARY_FIRST_ROW + w
            ar = blk["avg_row"]
            vals = {}
            vals["week"] = blk["week"]
            vals["starts"] = f"={start}+{7 * w}"
            vals["phase"] = (f'=IFERROR(LOOKUP({w + 1},{self.ref["phase_starts"]},{self.ref["phase_names"]}),"")'
                             if "phase_starts" in self.ref else "")
            vals["planned"] = planned[w] if isinstance(planned, list) and w < len(planned) else \
                (planned[-1] if isinstance(planned, list) else planned)
            if "session_done" in self.col_of:
                L = get_column_letter(self.col_of["session_done"])
                vals["done"] = f'=IF({ct}!{L}{ar}="","",{ct}!{L}{ar})'
            else:
                vals["done"] = ""
            D, E = self.scol["planned"], self.scol["done"]
            vals["attendance"] = f'=IF(OR({E}{rr}="",{D}{rr}="",{D}{rr}=0),"",MIN(1,{E}{rr}/{D}{rr}))'
            for k, _ in AVG_FIELDS:
                if f"avg_{k}" in self.scol:
                    L = get_column_letter(self.col_of[k])
                    vals[f"avg_{k}"] = f'=IF({ct}!{L}{ar}="","",{ct}!{L}{ar})'
            if "weight_change" in self.scol:
                W = self.scol["avg_weight"]
                vals["weight_change"] = "" if w == 0 else f'=IF(OR({W}{rr}="",{W}{rr - 1}=""),"",{W}{rr}-{W}{rr - 1})'
            if "symptom_days" in self.scol:
                L = get_column_letter(self.col_of["symptoms"])
                d0, d1 = blk["days"]
                rng = f"{ct}!{L}{d0}:{L}{d1}"
                vals["symptom_days"] = (f'=IF(COUNTA({rng})=0,"",COUNTIFS({rng},"<>",{rng},"<>none",{rng},"<>no"))')
            qr = blk["q_rows"][win_q]
            vals["win"] = f'=IF({ct}!D{qr}="","",{ct}!D{qr})'
            cr = blk["c_rows"][1]
            vals["changes"] = f'=IF({ct}!D{cr}="","",{ct}!D{cr})'
            for i, (k, _, _) in enumerate(self.scols, start=1):
                fmt = {"starts": "dd mmm", "attendance": "0%", "weight_change": "+0.0;-0.0;0.0",
                       "avg_steps": "#,##0", "avg_calories": "#,##0"}.get(k)
                fill = st.fill("input_bg") if k == "planned" else st.fill("calc_bg")
                sh.cell(rr, i, vals.get(k, ""), fill=fill, border=True, font=st.font(size=9, bold=(k == "week")),
                        align=WRAP_TOP if k in ("win", "changes") else WRAP_CENTER, fmt=fmt)
            sh.ws.row_dimensions[rr].height = 30
        first, last = SUMMARY_FIRST_ROW, SUMMARY_FIRST_ROW + self.weeks - 1
        F = self.scol["attendance"]
        sh.ws.conditional_formatting.add(
            f"{F}{first}:{F}{last}", FormulaRule(formula=[f"AND(ISNUMBER({F}{first}),{F}{first}<0.5)"],
                                                 fill=st.cf("alert_bg")))
        sh.ws.conditional_formatting.add(
            f"{F}{first}:{F}{last}", FormulaRule(formula=[f"AND(ISNUMBER({F}{first}),{F}{first}>=0.8)"],
                                                 fill=st.cf("good_bg")))
        if "symptom_days" in self.scol:
            S = self.scol["symptom_days"]
            sh.ws.conditional_formatting.add(
                f"{S}{first}:{S}{last}", FormulaRule(formula=[f"AND(ISNUMBER({S}{first}),{S}{first}>0)"],
                                                     fill=st.cf("alert_bg")))
        sh.ws.freeze_panes = sh.ws.cell(first, 2)
        self.add_tab_purpose(sh.title, "Automatic weekly trends: attendance, weight, steps, sleep, energy")

    # ---------------- Measurements (centimetres and inches)
    def build_measurements(self):
        tr = self.p.get("tracking", {})
        sites = tr.get("measurement_sites", DEFAULT_MEASUREMENT_SITES)
        every = int(tr.get("measure_every_weeks", 2))
        cps = list(tr.get("measurement_checkpoints") or ([0] + list(range(every, self.weeks + 1, every))))
        if self.weeks not in cps:
            cps.append(self.weeks)
        ncp = len(cps)
        widths = [32, 8] + [9] * ncp + [11, 40]
        sh = Sheet(self.wb, TAB["measurements"], self.st, len(widths), widths)
        st = self.st
        sh.title_block("Measurements",
                       "Optional but useful: the tape often shows progress when the scale doesn't. Measure in "
                       "centimetres or inches — choose below, and the sheet shows both.")
        sh.band("How to measure — the same way every time", "neutral", gap_before=False)
        sh.bullets(tr.get("measurement_guide", DEFAULT_MEASUREMENT_GUIDE))
        sh.band("Your measurements", "neutral")
        # unit selector
        ur = sh.row
        default_unit = normalise_length_unit(tr.get("measurement_unit") or self.units.get("length", "cm"))
        sh.cell(ur, 1, "I measure in (choose cm or in):", font=st.font(st.c["primary"], True),
                fill=st.fill("info_bg"), border=True)
        sh.cell(ur, 2, default_unit, font=st.font(bold=True), fill=st.fill("input_bg"), border=True,
                align=WRAP_CENTER)
        dv = DataValidation(type="list", formula1='"cm,in"', allow_blank=False)
        dv.error = "Choose cm or in"
        dv.showErrorMessage = True
        dv.add(f"B{ur}")
        sh.ws.add_data_validation(dv)
        sh.cell(ur, 3, "Write every measurement in this unit. The second table converts it automatically "
                       "(1 inch = 2.54 cm). Body weight stays in kg.",
                font=st.font(st.c["muted"], italic=True, size=9))
        sh.merge(ur, 3, len(widths))
        sh.ws.row_dimensions[ur].height = 20
        U = f"$B${ur}"
        self.ref["length_unit"] = f"{q(TAB['measurements'])}!{U}"
        start = self.ref["start"]
        r = ur + 2
        hdr = ["Site", "Unit"] + [("Start" if c == 0 else f"After wk {c}") for c in cps] + \
              ["Total change", "Landmark"]
        for i, h in enumerate(hdr, start=1):
            sh.cell(r, i, h, font=st.font("FFFFFF", True, 9), fill=st.fill("neutral"), align=WRAP_CENTER,
                    border=True)
        r += 1
        sh.cell(r, 1, "Date (approx.)", font=st.font(st.c["muted"], italic=True, size=9), border=True)
        sh.cell(r, 2, "", border=True)
        for i, c in enumerate(cps):
            sh.cell(r, 3 + i, f"={start}+{7 * c}", fmt="dd mmm", fill=st.fill("calc_bg"), border=True,
                    font=st.font(size=9), align=WRAP_CENTER)
        date_row = r
        r += 1
        firstL, lastL = get_column_letter(3), get_column_letter(2 + ncp)
        tot_col = 3 + ncp
        totL = get_column_letter(tot_col)
        length_rows = []
        for s in sites:
            unit = str(s.get("unit", "length"))
            is_length = unit.lower() in ("length", "cm", "in", "inch", "inches", "")
            sh.cell(r, 1, s["site"], font=st.font(bold=True, size=9), border=True)
            sh.cell(r, 2, f"={U}" if is_length else unit, font=st.font(size=9), border=True, align=WRAP_CENTER)
            for i in range(ncp):
                sh.cell(r, 3 + i, fill=st.fill("input_bg"), border=True, font=st.font(size=9), align=WRAP_CENTER)
            sh.cell(r, tot_col,
                    f'=IF(OR({firstL}{r}="",COUNT({firstL}{r}:{lastL}{r})<2),"",'
                    f'INDEX({firstL}{r}:{lastL}{r},MATCH(9.99E+307,{firstL}{r}:{lastL}{r}))-{firstL}{r})',
                    fill=st.fill("calc_bg"), border=True, font=st.font(bold=True, size=9),
                    fmt="+0.0;-0.0;0.0", align=WRAP_CENTER)
            sh.cell(r, tot_col + 1, s.get("landmark", ""), border=True, font=st.font(st.c["muted"], size=9))
            r2 = r + 1
            sh.cell(r2, 1, "   change vs previous", font=st.font(st.c["muted"], italic=True, size=8), border=True)
            sh.cell(r2, 2, "", border=True)
            sh.cell(r2, 3, "", border=True, fill=st.fill("calc_bg"))
            for i in range(1, ncp):
                L, P = get_column_letter(3 + i), get_column_letter(2 + i)
                sh.cell(r2, 3 + i, f'=IF(OR({L}{r}="",{P}{r}=""),"",{L}{r}-{P}{r})', fill=st.fill("calc_bg"),
                        border=True, font=st.font(st.c["muted"], size=8), fmt="+0.0;-0.0;0.0", align=WRAP_CENTER)
            sh.cell(r2, tot_col, "", border=True)
            sh.cell(r2, tot_col + 1, "", border=True)
            sh.ws.row_dimensions[r].height = 18
            sh.ws.row_dimensions[r2].height = 13
            if is_length:
                length_rows.append((s["site"], r))
            r += 2
        sh.cell(r, 1, "Progress photos taken (only with your consent: Y/N)", font=st.font(bold=True, size=9),
                border=True)
        sh.cell(r, 2, "", border=True)
        for i in range(ncp):
            sh.cell(r, 3 + i, fill=st.fill("input_bg"), border=True, font=st.font(size=9), align=WRAP_CENTER)
        sh.ws.row_dimensions[r].height = 26
        # converted table (automatic)
        if length_rows:
            r += 2
            sh.band(f'="Same measurements in "&IF({U}="cm","inches","centimetres")&" — calculates itself"',
                    "neutral_light", row=r)
            r += 1
            hdr2 = ["Site", "Unit"] + [("Start" if c == 0 else f"After wk {c}") for c in cps] + ["Total change", ""]
            for i, h in enumerate(hdr2, start=1):
                sh.cell(r, i, h, font=st.font("FFFFFF", True, 9), fill=st.fill("neutral_light"), align=WRAP_CENTER,
                        border=True)
            r += 1
            for i in range(ncp):
                L = get_column_letter(3 + i)
                sh.cell(r, 3 + i, f"={L}{date_row}", fmt="dd mmm", fill=st.fill("calc_bg"), border=True,
                        font=st.font(size=9), align=WRAP_CENTER)
            sh.cell(r, 1, "Date (approx.)", font=st.font(st.c["muted"], italic=True, size=9), border=True)
            sh.cell(r, 2, "", border=True)
            r += 1
            for site, src in length_rows:
                sh.cell(r, 1, site, font=st.font(bold=True, size=9), border=True)
                sh.cell(r, 2, f'=IF({U}="cm","in","cm")', font=st.font(size=9), border=True, align=WRAP_CENTER)
                for i in range(ncp):
                    L = get_column_letter(3 + i)
                    sh.cell(r, 3 + i, f'=IF({L}{src}="","",ROUND(IF({U}="cm",{L}{src}/2.54,{L}{src}*2.54),1))',
                            fill=st.fill("calc_bg"), border=True, font=st.font(size=9), fmt="0.0", align=WRAP_CENTER)
                sh.cell(r, tot_col,
                        f'=IF({totL}{src}="","",ROUND(IF({U}="cm",{totL}{src}/2.54,{totL}{src}*2.54),1))',
                        fill=st.fill("calc_bg"), border=True, font=st.font(bold=True, size=9),
                        fmt="+0.0;-0.0;0.0", align=WRAP_CENTER)
                sh.ws.row_dimensions[r].height = 16
                r += 1
        sh.row = r + 1
        if tr.get("measurement_note"):
            sh.note(tr["measurement_note"])
        self.add_tab_purpose(sh.title, "Body measurements in cm or inches (both shown), with a measuring guide")

    # ---------------- Progress reviews
    def build_reviews(self):
        rv = self.p.get("reviews", {})
        every = int(rv.get("every_weeks", 4))
        cps = list(rv.get("checkpoints") or range(every, self.weeks + 1, every))
        if not cps or cps[-1] != self.weeks:
            cps.append(self.weeks)
        widths = [34, 14] + [14] * len(cps) + [30]
        sh = Sheet(self.wb, TAB["reviews"], self.st, len(widths), widths)
        sh.title_block("Progress Reviews",
                       rv.get("subtitle", "A short review every few weeks. Strength, energy and consistency are "
                                          "tracked separately from appearance."))
        sh.ws.freeze_panes = "B5"
        hdr = ["Measure", "Baseline"] + [f"Week {self.first_week + c - 1}" for c in cps] + ["Notes"]
        sq = q(TAB["summary"])

        def rng(key, a, b):
            L = self.scol[key]
            return f"{sq}!${L}${SUMMARY_FIRST_ROW + a - 1}:${L}${SUMMARY_FIRST_ROW + b - 1}"

        sh.band("A. Consistency (calculated from the Weekly Summary)", "neutral", gap_before=False)
        prev, att, done = 1, [], []
        for c in cps:
            att.append(f'=IFERROR(AVERAGE({rng("attendance", prev, c)}),"—")')
            done.append(f'=IF(COUNT({rng("done", prev, c)})=0,"—",SUM({rng("done", prev, c)}))')
            prev = c + 1
        first, _ = sh.table(hdr, [["Average attendance", "—"] + att + [""],
                                  ["Sessions completed", "—"] + done + [""]],
                            calc_cols=tuple(range(2, 2 + len(cps))))
        for i in range(len(cps)):
            sh.ws.cell(first, 3 + i).number_format = "0%"
        for title, items, color in (
                ("B. Strength — write the version and reps (e.g. 'Knee push-up 3 × 10')",
                 rv.get("strength_markers", ["Squat — version, weight × reps", "Push-up — surface × reps",
                                             "Row — weight × reps", "Hinge / bridge — version × reps",
                                             "Core — exercise × time or reps"]), "neutral"),
                ("C. How it feels (1 = poor, 5 = great)",
                 rv.get("feel_markers", ["Moving comfortably day to day", "Energy and recovery", "Sleep",
                                         "Enjoying the training", "Confidence with food choices"]), "neutral"),
                ("D. Body — optional (copy from Measurements)",
                 rv.get("body_markers", [f"Weekly average weight ({self.units['weight']})",
                                         "Waist at navel (cm / in — see Measurements)"]), "neutral"),
                ("E. Coach decision for the next block", ["What we keep", "What we change", "Next focus"], "coach"),
        ):
            sh.band(title, color)
            sh.table(hdr, [[x, ""] + [""] * len(cps) + [""] for x in items],
                     input_cols=tuple(range(1, 2 + len(cps))))
        self.add_tab_purpose(sh.title, "Progress check every few weeks: consistency, strength, how you feel")

    # ---------------- Change log
    def build_changelog(self):
        cl = self.p.get("changelog", [])
        sh = Sheet(self.wb, TAB["changelog"], self.st, 5, [13, 10, 48, 48, 16])
        sh.title_block("Change Log", "Every change to your plan, when and why — so we can see what worked.")
        sh.ws.freeze_panes = "A5"
        rows = [[c.get("date", ""), c.get("version", ""), c.get("change", ""), c.get("why", ""),
                 c.get("requested_by", "")] for c in cl]
        rows += [["", "", "", "", ""] for _ in range(max(5, 15 - len(rows)))]
        sh.table(["Date", "Version", "What changed", "Why", "Requested by"], rows, input_cols=(0, 1, 2, 3, 4),
                 bold_first=False)
        self.add_tab_purpose(sh.title, "History of plan changes and the reasons for them")

    # ---------------- Coach-only tabs
    def build_coach_notes(self):
        cn = self.p.get("coach_notes", {})
        sh = Sheet(self.wb, TAB["coach"], self.st, 5, [26, 44, 40, 36, 16])
        sh.title_block("Coach Notes — coach only",
                       "Reasoning, health considerations and how to adjust. Not included in the client copy.")
        sh.ws.freeze_panes = "A5"
        if cn.get("triage"):
            sh.band("Safety triage", "home", gap_before=False)
            sh.kv([("Level", cn["triage"].get("level", "")), ("Why", cn["triage"].get("why", "")),
                   ("Deferred until cleared", cn["triage"].get("deferred", "None"))])
        if cn.get("health"):
            sh.band("Health considerations & modifications", "coach")
            sh.table(["Area", "What we know", "In training / nutrition", "Refer or review if…", "Status"],
                     [[h.get("area"), h.get("known"), h.get("plan"), h.get("review_if"), h.get("status")]
                      for h in cn["health"]])
        if cn.get("guidance"):
            sh.band("Coaching guidance", "coach")
            sh.table(["Topic", "Guidance"], [list(x) for x in cn["guidance"]], spans=[1, 4])
        en = cn.get("energy")
        if en:
            sh.band("Energy & protein estimate — adjustable starting estimate, not a prescription", "coach")
            r = sh.row
            sex = str(en.get("sex", "female")).lower()
            const = 5 if sex.startswith("m") else -161
            items = [("Body weight (kg)", en.get("weight_kg")), ("Height (cm)", en.get("height_cm")),
                     ("Age (years)", en.get("age")), ("Activity factor — low", en.get("activity_low", 1.4)),
                     ("Activity factor — high", en.get("activity_high", 1.55)),
                     ("Protein (g per kg body weight)", en.get("protein_g_per_kg", 1.6)),
                     ("Planned deficit (kcal/day, 0 = maintenance)", en.get("deficit", 0))]
            for i, (lab, v) in enumerate(items):
                sh.cell(r + i, 1, lab, font=self.st.font(bold=True), border=True, fill=self.st.fill("info_bg"))
                sh.cell(r + i, 2, v, border=True, fill=self.st.fill("input_bg"))
            R = r + len(items)
            calc = [
                ("Resting energy (Mifflin-St Jeor)", f"=ROUND(10*B{r}+6.25*B{r + 1}-5*B{r + 2}{const:+d},0)",
                 f"kcal/day — 10×kg + 6.25×cm − 5×age {const:+d} ({'men' if const > 0 else 'women'})"),
                ("Estimated maintenance — low", f"=ROUND(B{R}*B{r + 3},-1)", "kcal/day"),
                ("Estimated maintenance — high", f"=ROUND(B{R}*B{r + 4},-1)", "kcal/day"),
                ("Starting intake — low", f"=ROUND(B{R + 1}-B{r + 6},-1)", "kcal/day"),
                ("Starting intake — high", f"=ROUND(B{R + 2}-B{r + 6},-1)", "kcal/day"),
                ("Working protein target", f"=ROUND(B{r}*B{r + 5}/5,0)*5", "g/day (rounded to nearest 5)"),
            ]
            for i, (lab, f, u) in enumerate(calc):
                sh.cell(R + i, 1, lab, font=self.st.font(bold=True), border=True, fill=self.st.fill("info_bg"))
                sh.cell(R + i, 2, f, border=True, fill=self.st.fill("calc_bg"), font=self.st.font(bold=True))
                sh.cell(R + i, 3, u, font=self.st.font(self.st.c["muted"]))
                sh.merge(R + i, 3, 5)
            sh.row = R + len(calc)
            sh.note(en.get("note", "Equations are often off by ±10–15% for an individual. Adjust from 2–3 weeks of "
                                   "weight/waist trend, hunger, energy and training performance — not one weigh-in."))
        if cn.get("to_confirm"):
            sh.band("Still to confirm", "coach")
            sh.bullets(cn["to_confirm"])
        if cn.get("adjust_if"):
            sh.band("Adjust the plan if…", "coach")
            sh.table(["If…", "Then…"], [list(x) for x in cn["adjust_if"]], spans=[2, 3])
        self.add_tab_purpose(sh.title, "Coach only: reasoning, health notes, energy estimate, adjustments")

    def build_evidence(self):
        ev = self.p.get("evidence", [])
        sh = Sheet(self.wb, TAB["evidence"], self.st, 6, [24, 40, 13, 40, 34, 34])
        sh.title_block("Evidence & Sources — coach only",
                       "What each key recommendation rests on. Grades: Strong / Moderate / Limited / Traditional / "
                       "Expert consensus. Sources were checked when the plan was built; re-check before relying on "
                       "them months later.")
        sh.ws.freeze_panes = "A5"
        rows = [[e.get("topic"), e.get("recommendation"), e.get("grade"), e.get("source"),
                 (e.get("url"), e.get("url")) if e.get("url") else "", e.get("notes", "")] for e in ev]
        sh.table(["Topic", "Recommendation", "Grade", "Source (organisation / authors, year)", "Link", "Notes"],
                 rows, link_cols=(4,))
        self.add_tab_purpose(sh.title, "Coach only: the sources behind each recommendation")

    def build_decisions(self):
        dl = self.p.get("decisions", [])
        sh = Sheet(self.wb, TAB["decisions"], self.st, 7, [26, 38, 26, 40, 12, 12, 12])
        sh.title_block("Decision Log — coach only",
                       "Choices where the evidence or expert opinion differs, and what the coach approved.")
        sh.ws.freeze_panes = "A5"
        rows = [[d.get("decision"), d.get("options"), d.get("chosen"), d.get("why"), d.get("grade", ""),
                 d.get("approved", ""), d.get("date", "")] for d in dl]
        sh.table(["Decision", "Options considered", "Chosen", "Why", "Evidence", "Coach approved", "Date"], rows)
        self.add_tab_purpose(sh.title, "Coach only: decisions with conflicting evidence and what was approved")

    def build_data(self):
        ws = self.wb.create_sheet(TAB["data"])
        blob = json.dumps(self.original_plan, ensure_ascii=False)
        ws["A1"] = "Plan JSON (do not edit by hand). Read with scripts/read_workbook.py --plan-json"
        for i, ch in enumerate([blob[j:j + 30000] for j in range(0, len(blob), 30000)], start=2):
            ws.cell(i, 1, ch)
        ws.sheet_state = "hidden"

    # ---------------- orchestration
    def build(self):
        self.create_overview()
        for s in self.p.get("sessions", []):
            self.build_session(s)
        self.build_progression()
        self.build_nutrition()
        self.build_supplements()
        self.build_lifestyle()
        # The Overview dashboard references Weekly Summary ranges, whose layout is fixed by
        # summary_columns(); the Check-in Tracker needs the Overview's start date and schedule.
        self.fill_overview()
        self.build_checkin()
        self.build_summary()
        self.build_measurements()
        self.build_reviews()
        self.build_changelog()
        if not self.client_copy:
            self.build_coach_notes()
            self.build_evidence()
            self.build_decisions()
            self.build_data()
        self.write_tab_guide()
        self.wb.active = 0
        return self.wb


# --------------------------------------------------------------------------------------
MAIN_SKILL = "fitness-lifestyle-coach"


def find_brand_file() -> Path:
    """brand.json lives in the main skill. Phase skills installed next to it use the main copy, so the
    coach edits branding in one place; otherwise they fall back to their own copy."""
    skill_dir = Path(__file__).resolve().parent.parent
    for cand in (skill_dir.parent / MAIN_SKILL / "assets" / "brand.json", skill_dir / "assets" / "brand.json"):
        if cand.exists():
            return cand
    return skill_dir / "assets" / "brand.json"


def validate(plan: dict):
    errs = []
    meta = plan.get("meta", {})
    for k in ("client_name", "plan_title", "start_date"):
        if not meta.get(k):
            errs.append(f"meta.{k} is required")
    if not (meta.get("weeks") or meta.get("days")):
        errs.append("meta.weeks or meta.days is required")
    try:
        parse_date(meta.get("start_date"))
    except ValueError:
        errs.append("meta.start_date must be YYYY-MM-DD")
    tabs = set()
    for s in plan.get("sessions", []):
        t = safe_tab(s.get("tab", ""))
        if not t:
            errs.append("every session needs a 'tab' name")
        if t in tabs or t in TAB.values():
            errs.append(f"duplicate or reserved tab name: {t}")
        tabs.add(t)
        for bl in s.get("blocks", []):
            for ex in bl.get("exercises", []):
                if not ex.get("name"):
                    errs.append(f"exercise without a name in tab {t}")
    for it in plan.get("supplements", {}).get("items", []):
        for k in ("name", "evidence", "cautions"):
            if not it.get(k):
                errs.append(f"supplement/remedy '{it.get('name', '?')}' is missing '{k}' "
                            f"(every item needs an evidence grade and cautions)")
    unknown = [f for f in plan.get("tracking", {}).get("daily_fields", []) if f not in DAILY_FIELDS]
    if unknown:
        errs.append(f"unknown tracking.daily_fields: {unknown} (allowed: {sorted(DAILY_FIELDS)})")
    if errs:
        raise SystemExit("Plan JSON problems:\n  - " + "\n  - ".join(errs))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--out-dir", default=".")
    ap.add_argument("--brand", help="brand.json (defaults to ../assets/brand.json if present)")
    ap.add_argument("--copy", choices=["both", "coach", "client"], default="both")
    args = ap.parse_args()

    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    validate(plan)
    brand_path = Path(args.brand) if args.brand else find_brand_file()
    brand_over = json.loads(brand_path.read_text(encoding="utf-8")) if brand_path.exists() else {}
    brand = deep_merge(DEFAULT_BRAND, brand_over)
    brand = deep_merge(brand, plan.get("brand", {}))
    if brand.get("logo_path") and not Path(brand["logo_path"]).is_absolute():
        brand["logo_path"] = str((brand_path.parent / brand["logo_path"]).resolve())

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    meta = plan["meta"]
    base = re.sub(r'[\\/:*?"<>|]+', "-", f'{meta["client_name"]} - {meta["plan_title"]}').strip()
    if meta.get("version"):
        base += f' v{meta["version"]}'
    written = []
    if args.copy in ("both", "coach"):
        p = out / f"{base} (Coach).xlsx"
        Builder(plan, brand, client_copy=False).build().save(p)
        written.append(p)
    if args.copy in ("both", "client"):
        p = out / f"{base}.xlsx"
        Builder(plan, brand, client_copy=True).build().save(p)
        written.append(p)
    for p in written:
        print(p)


if __name__ == "__main__":
    main()
