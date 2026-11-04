# Client workbook — tabs, plan JSON schema, build & delivery

## Contents

1. Tabs and what they do
2. Colour conventions
3. Plan JSON schema
4. Build, verify, deliver (Excel + Google Sheets)
5. Editing an existing workbook

---

## 1. Tabs

| Tab                                | Copy  | Content                                                                                                                                                                                                                                                                                     |
| ---------------------------------- | ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Overview                           | both  | Dashboard (start/end/target dates, current week & phase, starting & latest weekly weight, sessions done, attendance, energy, sleep), colour key, weekly schedule by phase, top priorities, what to expect, listen-to-your-body rules, equipment, how check-ins work + contact, tab guide    |
| One tab per session (`sessions[]`) | both  | Info rows (objective, duration, warm-up, effort, cool-down…), one or more blocks (HOME terracotta / GYM slate / neutral) with pattern, exercise, cues, sets × reps per phase, rest, effort, easier, harder, if-it-bothers-you, video; "My notes"                                            |
| Progression                        | both  | Phases with auto dates; double progression; readiness checklist; exercise ladders; lighter weeks                                                                                                                                                                                            |
| Nutrition                          | both  | Targets (low/high), guides (plate, portions, medicine timing), structured meal plans with auto totals **and/or** flexible 7-day menu with auto protein totals, timing options, swap list, rules                                                                                             |
| Supplements & Remedies             | both  | Items with type, why for you, evidence grade, how to take, cautions, alternative, status; "not recommended (why)"; evidence-label legend; safety notes                                                                                                                                      |
| Lifestyle & Recovery               | both  | 2–3 starting habits; recovery basics; extra sections (busy weeks, migraine days…)                                                                                                                                                                                                           |
| Check-in Tracker                   | both  | One block per week: band with dates + phase; 7 day rows (date, day, planned session auto-filled from the schedule, then the daily fields); "This week" totals/averages; weekly reflection questions (yellow); coach rows (grey): Coach notes, Changes for next week, Coach video/voice note |
| Weekly Summary                     | both  | One row per week, all formulas: planned (editable), done, attendance %, averages, weight change, symptom days, client's win, coach's changes                                                                                                                                                |
| Measurements                       | both  | Measuring guide; a **cm / in dropdown** (client records in either unit); sites × checkpoints (start + every N weeks) with change vs previous and total change; a second table showing every length converted to the other unit automatically; photo-consent row. Body weight stays in kg |
| Progress Reviews                   | both  | Every 4 weeks: consistency (auto), strength markers, how it feels, body (optional), coach decision                                                                                                                                                                                          |
| Change Log                         | both  | Date · version · what changed · why · requested by                                                                                                                                                                                                                                          |
| Coach Notes                        | coach | Triage, health table (known / plan / review-if / status), coaching guidance, live energy & protein calculator, still-to-confirm, adjust-if table                                                                                                                                            |
| Evidence & Sources                 | coach | Topic · recommendation · grade · source · link · notes                                                                                                                                                                                                                                      |
| Decision Log                       | coach | Contested decisions, options, chosen, why, grade, approved, date                                                                                                                                                                                                                            |
| \_plan_data (hidden)               | coach | The plan JSON — lets the plan be re-read (`read_workbook.py --plan-json`) and rebuilt                                                                                                                                                                                                       |

## 2. Colours

Yellow = client fills in · green-grey = calculates itself · terracotta = home version · slate =
gym version · dark green = general · grey = coach writes here. Font Arial. Override colours/fonts
in `assets/brand.json` → `colors` (hex without #) if the coach has brand colours.

## 3. Plan JSON schema

Only `meta` is required; every other section is optional (omit what the plan doesn't need).
Text fields accept plain text; keep client-facing text in plain English.

```jsonc
{
  "meta": {
    "client_name": "Asha", // required — use the name the coach uses
    "plan_title": "12-Week Strength Plan", // required
    "subtitle": "One-line purpose of the plan",
    "start_date": "2026-11-09", // required, YYYY-MM-DD (Day 1; Mondays work best)
    "weeks": 12, // or "days": 14 for short plans
    "target_date": "2027-02-10", // optional event/target
    "starting_weight": 72.4, // optional; baseline for "change since start"
    "units": { "weight": "kg", "length": "cm" }, // length = default entry unit on the Measurements tab ("cm" or "in"); the sheet always shows both
    "version": "1.0",
    "first_week_number": 1, // continue numbering in a new block (e.g. 16)
  },
  "brand": {}, // optional per-plan override of assets/brand.json
  "overview": {
    "schedule_mode": "weekday", // "weekday" (Day = Monday…Sunday) or "day_number" (Day 1…N rows)
    "schedule_title": "Your week",
    "phase_columns": ["Weeks 1–2", "Weeks 3–8"], // up to 4
    "schedule": [
      {
        "day": "Monday",
        "session": "Lower body",
        "tab": "Mon - Lower Body",
        "time": "35 min",
        "phases": { "Weeks 1–2": "Core", "Weeks 3–8": "Core" },
      },
    ],
    "schedule_note": "…",
    "priorities": ["1. …"],
    "expectations": ["…"],
    "listen_to_body": ["…"],
    "equipment": "…",
    "checkin_instructions": ["…"], // overrides brand.json instructions
  },
  "sessions": [
    {
      "tab": "Mon - Lower Body", // ≤ 31 chars, unique, no []:*?/\ ; becomes the tab name
      "kind": "workout", // "workout" (adds My notes) | "mobility" | "busy"
      "title": "Monday — Lower Body + Core",
      "subtitle": "…",
      "purpose": "shown in the tab guide",
      "info": [
        ["Objective", "…"],
        ["Duration", "…"],
        ["Warm-up", "…"],
        ["Effort", "…"],
        ["Cool-down", "…"],
      ],
      "blocks": [
        {
          "label": "HOME VERSION · two 5 kg dumbbells, chair",
          "style": "home", // home | gym | neutral
          "prescription_labels": ["Weeks 1–2", "Weeks 3–4"],
          "exercises": [
            {
              "pattern": "Squat",
              "name": "Squat to chair",
              "cues": "…",
              "prescription": ["2 × 8–10", "3 × 8–12"],
              "rest": "60–90 s",
              "effort": "3–4 left → 2–3 left",
              "easier": "…",
              "harder": "…",
              "if_bothers": "…",
              "video": "https://www.youtube.com/watch?v=…",
            },
          ],
          "note": "optional note under the table",
        },
      ],
      "footer": "…",
      "my_notes": true,
      "my_notes_questions": ["…"],
    },
  ],
  "progression": {
    "title": "…",
    "subtitle": "…",
    "phases": [
      {
        "name": "Phase 1 — Foundation",
        "start_week": 1,
        "end_week": 4,
        "sessions": "…",
        "aim": "…",
        "sets_effort": "…",
      },
    ], // weeks relative to this block
    "sections": [
      { "title": "…", "bullets": ["…"] },
      { "title": "…", "table": { "headers": ["…", "…"], "rows": [["…", "…"]] } },
    ],
  },
  "nutrition": {
    "title": "…",
    "subtitle": "…",
    "targets": [
      { "what": "Protein", "target": "About 95 g", "low": 85, "high": 115, "why": "…" },
    ],
    "guides": [
      ["Plate guide", "…"],
      ["Portion guide", "…"],
    ],
    "meal_plans": [
      {
        // STRUCTURED style (any number, e.g. training / rest day)
        "title": "Training day — ~1,700 kcal",
        "style": "home",
        "intro": "…",
        "meals": [
          {
            "meal": "Meal 1",
            "time": "8 am",
            "items": [
              {
                "food": "Moong chilla",
                "qty": "2 medium (60 g dal)",
                "protein": 13,
                "carbs": 30,
                "fat": 8,
                "fibre": 6,
                "kcal": 240,
                "alternative": "2 besan chilla",
                "notes": "…",
              },
            ],
          },
        ],
        "note": "…",
      },
    ],
    "menu": {
      // FLEXIBLE style
      "title": "…",
      "slots": ["Breakfast", "Lunch", "Dinner", "Snack"], // 3–5 slots
      "days": [
        {
          "day": "Day 1",
          "breakfast": ["Poha + 2 eggs", 17],
          "lunch": ["…", 20],
          "dinner": ["…", 22],
          "snack": ["…", 6],
          "swaps": "…",
        },
      ],
      "note": "…",
    },
    "timing": [
      { "option": "A", "when": "Train before dinner", "what": "…", "notes": "…" },
    ],
    "swaps": [
      {
        "food": "Eggs",
        "portion": "2 whole",
        "protein": 12,
        "kcal": 140,
        "swap": "75 g paneer",
      },
    ],
    "sections": [{ "title": "Keep it flexible", "bullets": ["…"] }],
  },
  "supplements": {
    "intro": ["Food first…"],
    "items": [
      {
        "name": "Methi seed water",
        "type": "Home remedy",
        "why_for_you": "…",
        "evidence": "Moderate",
        "how": "…",
        "cautions": "…", // evidence + cautions REQUIRED
        "alternative": "…",
        "status": "Coach-approved, optional",
      },
    ],
    "not_recommended": [{ "name": "ACV shots", "why": "…" }],
    "safety_notes": ["…"], // optional; sensible defaults otherwise
  },
  "lifestyle": {
    "habits": [{ "habit": "1. Walk after meals", "what": "…", "why": "…" }], // 2–3 only
    "recovery": [
      ["Sleep", "…"],
      ["Caffeine", "…"],
    ],
    "sections": [{ "title": "Busy week — minimum plan", "bullets": ["…"] }],
  },
  "tracking": {
    "daily_fields": [
      "session_done",
      "weight",
      "steps",
      "sleep_hours",
      "nutrition",
      "hydration",
      "energy",
      "off_plan",
      "symptoms",
      "notes",
    ],
    // allowed: session_done weight steps sleep_hours sleep_quality nutrition protein calories
    //          water hydration energy stress off_plan symptoms notes
    "weekly_reflection": ["What got in the way this week?", "…"], // the win question feeds the Weekly Summary
    "sessions_planned": [3, 3, 5, 5], // per week (count every activity they should tick, incl. mobility/walk days) or one number
    "checkin_day": "Sunday",
    "checkin_intro": "…",
    "measure_every_weeks": 2, // or "measurement_checkpoints": [0, 4, 8, 12]
    "measurement_unit": "in",              // optional override of meta.units.length for this client
    "measurement_sites": [{ "site": "Waist (at navel)", "unit": "length", "landmark": "…" }],  // unit "length" (cm/in, converted) or "kg"
    "measurement_guide": ["…"],
    "measurement_note": "…",
  },
  "reviews": {
    "every_weeks": 4,
    "strength_markers": ["…"],
    "feel_markers": ["…"],
    "body_markers": ["…"],
  },
  "changelog": [
    {
      "date": "2026-11-08",
      "version": "1.0",
      "change": "First plan",
      "why": "…",
      "requested_by": "Coach",
    },
  ],
  "coach_notes": {
    "triage": {
      "level": "B — coaching with precautions",
      "why": "…",
      "deferred": "None",
    },
    "health": [
      {
        "area": "…",
        "known": "…",
        "plan": "…",
        "review_if": "…",
        "status": "Client-stated",
      },
    ],
    "guidance": [["Why this split", "…"]],
    "energy": {
      "sex": "female",
      "weight_kg": 72,
      "height_cm": 160,
      "age": 34,
      "activity_low": 1.4,
      "activity_high": 1.55,
      "protein_g_per_kg": 1.4,
      "deficit": 400,
      "note": "…",
    },
    "to_confirm": ["…"],
    "adjust_if": [["Attendance < 50% for 2 weeks", "…"]],
  },
  "evidence": [
    {
      "topic": "…",
      "recommendation": "…",
      "grade": "Strong",
      "source": "Author, Journal, Year",
      "url": "https://…",
      "notes": "…",
    },
  ],
  "decisions": [
    {
      "decision": "…",
      "options": "…",
      "chosen": "…",
      "why": "…",
      "grade": "…",
      "approved": "Y",
      "date": "2026-11-08",
    },
  ],
}
```

Guidance:

- **Sessions:** `prescription_labels` = the phase columns for sets × reps (2–4). Use the same
  labels across a tab's blocks. HOME and GYM versions of the same session go in one tab as two
  blocks.
- **Videos:** use `exercise-library.md` links; otherwise only a URL you have seen in search
  results; else omit (builder adds a labelled YouTube search link).
- **Schedule tab names** in `overview.schedule[].tab` should match real tab names (or another
  tab such as "Check-in Tracker").
- **Short plans** (e.g. 14 days with Day 1…Day 14 rows): `"days": 14` and
  `"schedule_mode": "day_number"` with one schedule row per day in order.
- **Coach-only content** (`coach_notes`, `evidence`, `decisions`) never appears in the client copy.

## 4. Build, verify, deliver

```
python scripts/build_workbook.py plan.json --out-dir "<client folder>"   # both copies
python scripts/build_workbook.py plan.json --out-dir … --copy coach      # coach copy only
python scripts/check_workbook.py "<client folder>"/*.xlsx                 # recalculates via LibreOffice, reports errors
```

- `assets/brand.json` is applied automatically (`--brand other.json` to override).
- The builder validates the JSON (missing required fields, duplicate tab names, supplements
  without evidence grade or cautions, unknown tracking fields) and stops with a clear message.
- Requires Python 3 + openpyxl (pre-installed on claude.ai; otherwise `pip install openpyxl`).

**Google Sheets:** upload the client `.xlsx` to Google Drive → right-click → Open with → Google
Sheets (or enable Drive setting "Convert uploads"). Formulas, dropdowns, conditional highlights,
hyperlinks and frozen panes carry over. Share with the client as **Editor**; keep the coach copy
private. If a Google Drive connector is available in the session, offer to upload and convert.
Formulas use only Excel/Sheets-compatible functions (no XLOOKUP, LET, LAMBDA, dynamic arrays).

**Delivering:** give the coach both files, a 5-line summary (structure, key targets, what's
pending clinically, what to explain to the client first), and the share steps.

## 5. Editing an existing workbook

- While the client is logging in the live sheet, don't regenerate it (that would wipe their
  entries). Give an exact change list (followup-and-checkins.md §6) or edit cells with openpyxl in
  a copy and tell the coach what changed.
- For a new block, build a new versioned workbook (§7 of followup-and-checkins.md).
