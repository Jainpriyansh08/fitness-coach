#!/usr/bin/env python3
"""Keep the coach skills in sync with the main skill, and package them.

The main skill (skills/fitness-lifestyle-coach) is the single source of truth for references,
scripts and assets. Each phase skill gets copies of only the files listed for it in
tools/skills_manifest.json, and every SKILL.md gets the shared text blocks from tools/snippets/
injected between <!-- shared:NAME --> and <!-- /shared:NAME --> markers.

Usage (from the repository root):
    python tools/sync_skills.py            # update all skills in place
    python tools/sync_skills.py --check    # exit 1 if anything is out of sync (use before committing)
    python tools/sync_skills.py --dist     # sync, then build dist/<skill>.zip for claude.ai upload

Edit shared files only in the main skill or in tools/snippets/, then run this script.
"""
from __future__ import annotations

import argparse
import filecmp
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
KINDS = ("references", "scripts", "assets")
SKIP_IN_ZIP = {"evals", "__pycache__"}


def load_manifest():
    return json.loads((ROOT / "tools" / "skills_manifest.json").read_text(encoding="utf-8"))


def inject_snippets(text: str, snippets: dict[str, str]) -> str:
    for name, body in snippets.items():
        pattern = re.compile(rf"(<!-- shared:{re.escape(name)} -->)(.*?)(<!-- /shared:{re.escape(name)} -->)", re.S)
        text = pattern.sub(lambda m: f"{m.group(1)}\n{body.strip()}\n{m.group(3)}", text)
    return text


def plan_changes(manifest):
    """Return a list of (action, target, source_or_text) describing what sync would do."""
    changes = []
    snippets = {n: (ROOT / p).read_text(encoding="utf-8") for n, p in manifest["snippets"].items()}
    main = SKILLS / manifest["main"]
    all_skills = [manifest["main"], *manifest["phase_skills"].keys()]
    for name in all_skills:
        skill_md = SKILLS / name / "SKILL.md"
        if not skill_md.exists():
            changes.append(("missing", skill_md, None))
            continue
        cur = skill_md.read_text(encoding="utf-8")
        new = inject_snippets(cur, snippets)
        if new != cur:
            changes.append(("write_text", skill_md, new))
    for name, spec in manifest["phase_skills"].items():
        sdir = SKILLS / name
        for kind in KINDS:
            wanted = set(spec.get(kind, []))
            for fname in sorted(wanted):
                src, dst = main / kind / fname, sdir / kind / fname
                if not src.exists():
                    changes.append(("missing_source", src, None))
                elif not dst.exists() or not filecmp.cmp(src, dst, shallow=False):
                    changes.append(("copy", dst, src))
            kdir = sdir / kind
            if kdir.exists():
                for f in sorted(kdir.iterdir()):
                    if f.is_file() and f.name not in wanted:
                        changes.append(("remove", f, None))
    return changes


def apply(changes):
    for action, target, payload in changes:
        if action == "write_text":
            target.write_text(payload, encoding="utf-8")
        elif action == "copy":
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(payload, target)
        elif action == "remove":
            target.unlink()


def build_dist(manifest):
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    for name in [manifest["main"], *manifest["phase_skills"].keys()]:
        sdir = SKILLS / name
        zpath = dist / f"{name}.zip"
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
            for f in sorted(sdir.rglob("*")):
                rel = f.relative_to(SKILLS)
                if f.is_dir() or any(part in SKIP_IN_ZIP for part in rel.parts) or f.suffix == ".pyc":
                    continue
                z.write(f, rel.as_posix())
        print(f"built {zpath.relative_to(ROOT)}")


def dist_problems(manifest):
    """Report zips in dist/ that don't match the skill folders (only if dist/ exists)."""
    dist = ROOT / "dist"
    if not dist.exists():
        return []
    problems = []
    for name in [manifest["main"], *manifest["phase_skills"].keys()]:
        zpath = dist / f"{name}.zip"
        sdir = SKILLS / name
        want = {}
        for f in sorted(sdir.rglob("*")):
            rel = f.relative_to(SKILLS)
            if f.is_dir() or any(part in SKIP_IN_ZIP for part in rel.parts) or f.suffix == ".pyc":
                continue
            want[rel.as_posix()] = f.read_bytes()
        if not zpath.exists():
            problems.append(f"dist/{name}.zip is missing")
            continue
        with zipfile.ZipFile(zpath) as z:
            have = {n: z.read(n) for n in z.namelist()}
        if have != want:
            problems.append(f"dist/{name}.zip is stale")
    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="report differences and exit 1 if out of sync")
    ap.add_argument("--dist", action="store_true", help="also build dist/<skill>.zip files")
    args = ap.parse_args()
    manifest = load_manifest()
    changes = plan_changes(manifest)
    problems = [c for c in changes if c[0] in ("missing", "missing_source")]
    for action, target, _ in problems:
        print(f"ERROR {action}: {target.relative_to(ROOT)}", file=sys.stderr)
    if problems:
        sys.exit(2)
    if args.check:
        for action, target, _ in changes:
            print(f"out of sync ({action}): {target.relative_to(ROOT)}")
        stale = dist_problems(manifest) if not changes else []
        for msg in stale:
            print(f"out of sync: {msg} (run: python tools/sync_skills.py --dist)")
        if not changes and not stale:
            print("all skills in sync")
        sys.exit(1 if (changes or stale) else 0)
    apply(changes)
    for action, target, _ in changes:
        print(f"{action}: {target.relative_to(ROOT)}")
    if not changes:
        print("all skills in sync")
    if args.dist:
        build_dist(manifest)


if __name__ == "__main__":
    main()
