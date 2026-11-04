#!/usr/bin/env python3
"""Programmatic facts and checks for eval run outputs (used alongside the LLM graders).

Usage: python tests/eval_checks.py <run_dir>     (run_dir contains outputs/)
Prints JSON: files found, formula check result, client-copy tab check, key plan values read from
the coach copy's embedded plan JSON, and response statistics (lines, words in the client reply).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skills" / "fitness-lifestyle-coach" / "scripts"
COACH_ONLY = {"Coach Notes", "Evidence & Sources", "Decision Log", "_plan_data"}


def numbers(text):
    return [float(x.replace(",", "")) for x in re.findall(r"\d[\d,]*\.?\d*", str(text))]


def client_reply_words(resp: str):
    m = re.search(r"reply (?:to|for) (?:the )?client[^\n]*\n(.*?)(?:\n\*\*coach note|\n#+ *coach note|\n\*\*changes for next week|\Z)",
                  resp, re.I | re.S)
    if not m:
        return None
    body = re.sub(r"^[>\s]+", "", m.group(1), flags=re.M)
    return len(re.findall(r"\b[\w'’-]+\b", body))


def plan_facts(plan: dict) -> dict:
    meta = plan.get("meta", {})
    nut = plan.get("nutrition", {})
    targets = nut.get("targets", [])
    prot = [t for t in targets if "protein" in str(t.get("what", "")).lower()]
    cal = [t for t in targets if "calor" in str(t.get("what", "")).lower() or "kcal" in str(t.get("target", "")).lower()]
    sched = plan.get("overview", {}).get("schedule", [])
    training_days = [s for s in sched if s.get("tab") and s.get("tab") not in ("—", "-", "Check-in Tracker", "Weekly Check-in")
                     and not re.search(r"\brest\b|mobility|walk", str(s.get("session", "")), re.I)]
    sessions = plan.get("sessions", [])
    ex = [e for s in sessions for b in s.get("blocks", []) for e in b.get("exercises", [])]
    supp = plan.get("supplements", {})
    return {
        "meta": {k: meta.get(k) for k in ("client_name", "plan_title", "version", "start_date", "weeks", "days",
                                          "first_week_number", "starting_weight", "units")},
        "measurement_unit": plan.get("tracking", {}).get("measurement_unit"),
        "protein_targets": [{"target": t.get("target"), "low": t.get("low"), "high": t.get("high")} for t in prot],
        "calorie_targets": [{"target": t.get("target"), "low": t.get("low"), "high": t.get("high")} for t in cal],
        "energy_inputs": plan.get("coach_notes", {}).get("energy"),
        "schedule": [{"day": s.get("day"), "session": s.get("session"), "tab": s.get("tab")} for s in sched],
        "training_days_guess": [s.get("day") for s in training_days],
        "session_tabs": [s.get("tab") for s in sessions],
        "exercise_count": len(ex),
        "exercises_missing_cues_or_options": [e.get("name") for e in ex
                                              if not (e.get("cues") and e.get("easier") and e.get("harder"))],
        "exercise_names": [e.get("name") for e in ex],
        "videos": {"vetted": sum(1 for e in ex if e.get("video")), "missing(search link)": sum(1 for e in ex if not e.get("video"))},
        "supplement_items": [{"name": i.get("name"), "evidence": i.get("evidence"), "status": i.get("status")} for i in supp.get("items", [])],
        "not_recommended": [x.get("name") for x in supp.get("not_recommended", [])],
        "changelog": plan.get("changelog", []),
        "decisions": [d.get("decision") for d in plan.get("decisions", [])],
        "lifestyle_habits": [h.get("habit") for h in plan.get("lifestyle", {}).get("habits", [])],
        "health_areas": [h.get("area") for h in plan.get("coach_notes", {}).get("health", [])],
    }


def main():
    run = Path(sys.argv[1])
    out = run / "outputs"
    facts = {"run": str(run)}
    resp_path = out / "response.md"
    resp = resp_path.read_text(encoding="utf-8") if resp_path.exists() else ""
    facts["response"] = {"exists": resp_path.exists(), "lines_nonblank": sum(1 for l in resp.splitlines() if l.strip()),
                         "words": len(resp.split()), "client_reply_words": client_reply_words(resp)}
    xlsx = sorted(out.rglob("*.xlsx"))
    facts["xlsx"] = [str(p.relative_to(out)) for p in xlsx]
    coach = [p for p in xlsx if "(Coach)" in p.name]
    client = [p for p in xlsx if "(Coach)" not in p.name]
    if xlsx:
        r = subprocess.run([sys.executable, SCRIPTS / "check_workbook.py", *map(str, xlsx)], capture_output=True, text=True)
        facts["formula_check"] = {"exit": r.returncode, "output": r.stdout.strip()[-1500:]}
        from openpyxl import load_workbook
        facts["client_copy_coach_tabs"] = {p.name: sorted(COACH_ONLY & set(load_workbook(p, read_only=True).sheetnames))
                                           for p in client}
    if coach:
        with tempfile.TemporaryDirectory() as t:
            pj = Path(t) / "plan.json"
            r = subprocess.run([sys.executable, SCRIPTS / "read_workbook.py", str(coach[-1]), "--plan-json", str(pj)],
                               capture_output=True, text=True)
            if pj.exists():
                facts["plan"] = plan_facts(json.loads(pj.read_text(encoding="utf-8")))
            else:
                facts["plan_error"] = r.stderr[-500:]
    print(json.dumps(facts, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
