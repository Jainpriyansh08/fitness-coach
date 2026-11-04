# Fitness Coach — Claude skills for evidence-based client coaching

A suite of Claude skills that act as a senior fitness, nutrition and lifestyle coaching advisor for a
personal trainer — from a new client's intake form to the first consultation, the training +
nutrition plan (as an Excel / Google Sheets workbook), weekly check-ins, client questions and plan
updates. Built for Indian clients and food by default; English throughout.

The skills research every medical condition and every remedy or supplement before advising, grade
the evidence, never diagnose, and ask the coach to approve contested choices before anything reaches
a client.

## The skills

| Skill | Use it when | What you get |
|---|---|---|
| **`fitness-lifestyle-coach`** (main) | Anything, any stage — it works out where the client is | Every phase below in one skill |
| `coach-initial-evaluation` | A new client's intake form arrives | Coach's briefing · safety triage (A–D) · cited research on their conditions · 40–50 min consultation script with 8–12 questions · must-establish checklist · provisional direction |
| `coach-live-consultation` | You're in the consultation ("LIVE COACH MODE") or just finished | 4-line live replies (insight · next question · safety · why) · post-call profile update |
| `coach-plan-builder` | "CONSULTATION COMPLETE — BUILD THE PLAN" | Plan Decision Brief for your approval → coach + client workbooks |
| `coach-checkin-review` | Weekly check-in | Trend review, safety flags, a ready-to-paste reply for the client, at most 1–2 changes |
| `coach-client-questions` | A client asks something ("can I take ACV / creatine / methi water?") | WhatsApp-ready reply + private coach note with evidence grade and cautions |
| `coach-plan-update` | New medicine, pain, a swap, or the next block | Exact change list + Change Log line, or a new versioned workbook |

All seven share the same ground rules, references and scripts. The main skill holds the master
copies; the phase skills carry only what they need.

```
intake → coach-initial-evaluation → consultation (coach-live-consultation) → coach-plan-builder
      → weekly: coach-checkin-review · coach-client-questions · coach-plan-update → next block
```

## What the workbook contains

Overview dashboard · one tab per session (home and gym versions, cues, sets × reps by phase,
easier / harder / "if it bothers you", demo video) · Progression · Nutrition (structured gram-level
meal plan *or* flexible plate guide + Indian menu, swaps, eating out) · Supplements & Remedies
(evidence-graded with cautions) · Lifestyle & Recovery · Check-in Tracker (daily log, weekly
reflection, coach reply — one block per week) · Weekly Summary (automatic trends) · Measurements
(**centimetres or inches** — the client picks, the sheet shows both) · Progress Reviews · Change Log.
The coach copy adds Coach Notes, Evidence & Sources, Decision Log and the hidden plan data used for
rebuilding. Formulas work in both Excel and Google Sheets.

## Install

**claude.ai** — upload each zip from [`dist/`](dist/) under Skills in your Claude settings (start
with `fitness-lifestyle-coach.zip`; add the phase skills you want). Code execution must be enabled
so the workbook can be built. Skill files are read-only there, so keep your standing rules (see
below) in your Project instructions.

**Claude Code** — copy the skill folders into your personal skills folder:

```bash
mkdir -p ~/.claude/skills
```

```bash
cp -r skills/* ~/.claude/skills/
```

Then ask for a skill by name (e.g. `/coach-checkin-review`) or just describe the task.

## Make it yours

- `skills/fitness-lifestyle-coach/assets/brand.json` — your name, business, contact details,
  check-in instructions and logo (shown on every client workbook).
- `skills/fitness-lifestyle-coach/assets/coach-preferences.md` — your standing rules (things you
  always or never do), your Google Drive folder for client sheets, default units.
- After editing anything in the main skill or `tools/snippets/`, run `python tools/sync_skills.py
  --dist` to update the phase skills and the zips.

## Saving to Google Drive

Workbooks are `.xlsx` files. With Google Drive for desktop, the skills save straight into your
synced client folder (set the path in coach-preferences). Otherwise upload the client copy to your
Drive folder → Open with Google Sheets, and share it with the client as Editor. Keep the coach copy
private.

## Testing

- `python tests/test_scripts.py` — automated checks of the workbook builder (formulas recalculated
  with LibreOffice when installed), the cm/inch conversion, input validation, the check-in reader,
  and the wiring of all seven skills.
- `skills/*/evals/` — 17 test cases with simulated clients (diabetes + blood pressure, postpartum,
  thyroid + PCOS, knee osteoarthritis, a healthy lifter, exertional chest symptoms, disordered-eating
  signs) and golden-standard assertions. Results of the last run: [`tests/REPORT.md`](tests/REPORT.md).
  With Claude Code you can re-run them from a skill folder with `claude plugin eval .`.

## Privacy

Test clients in this repository are fictional. Never commit real client files — keep them in your
Google Drive client folder.
