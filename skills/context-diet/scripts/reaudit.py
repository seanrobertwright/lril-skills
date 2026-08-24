#!/usr/bin/env python3
"""context-diet re-audit: check the health of a previous pruning.

Answers the questions a second run actually needs, all of them measurable:

  orphans     references nothing points to (dead weight on disk)
  dangling    pointers whose target no longer exists (a broken promise)
  drift       extracted content that has reappeared in eager context
  regrowth    eager tokens climbing back toward the pre-prune figure
  dead rules  `paths:` globs that match nothing, so the rule never loads
  vague       pointers with no concrete trigger

On the "does this belong back in CLAUDE.md?" question: how often Claude
actually reads a reference is NOT observable from disk, and this tool does not
pretend otherwise. What it can do is flag pointers whose trigger is so broad
that the answer is probably yes, and hand you the judgement call.

Standard library only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from discover import (  # noqa: E402
    SKIP_DIRS, discover, effective_text, parse_paths_frontmatter,
    split_frontmatter,
)
from verify import (  # noqa: E402
    BACKTICKED_PATH_RE, INDEX_END, INDEX_START, glob_matches, repo_files,
)

# A pointer earns its keep by naming an observable trigger.
TRIGGER_RE = re.compile(r"^\s*-?\s*(before|when|whenever|after|if|while)\b", re.I)
# Triggers this broad describe "most sessions", which is an argument for
# putting the content back rather than referencing it.
TOO_BROAD_RE = re.compile(
    r"\b(always|any time|anytime|every session|all work|any task|generally)\b", re.I)


def eager_files(root: Path) -> list[Path]:
    inv, _ = discover(root)
    return [Path(f["path"]) for f in inv["files"] if f["eager"]], inv


def index_sections(files: list[Path]) -> dict[Path, str]:
    out = {}
    for f in files:
        if not f.is_file():
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        if INDEX_START in text and INDEX_END in text:
            out[f] = text.split(INDEX_START, 1)[1].split(INDEX_END, 1)[0]
    return out


def pointer_lines(section: str) -> list[str]:
    return [ln.strip() for ln in section.splitlines()
            if ln.strip().startswith("-") and BACKTICKED_PATH_RE.search(ln)]


def referenced_paths(root: Path, files: list[Path]) -> set[Path]:
    """Every .md path mentioned in backticks anywhere in eager context."""
    found: set[Path] = set()
    for f in files:
        if not f.is_file():
            continue
        for m in BACKTICKED_PATH_RE.finditer(
                f.read_text(encoding="utf-8", errors="replace")):
            p = Path(m.group(1))
            found.add(p if p.is_absolute() else (root / p))
    return {p.resolve() for p in found}


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".")
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args()

    root = Path(args.root).resolve()
    state = root / ".claude" / ".context-diet"
    findings: dict[str, list[str]] = {
        "orphans": [], "dangling": [], "drift": [],
        "regrowth": [], "dead_rules": [], "vague": [],
    }

    files, inv = eager_files(root)
    eager_now = inv["totals"]["eager_tokens"]

    manifest = None
    if (state / "manifest.json").is_file():
        manifest = json.loads((state / "manifest.json").read_text(encoding="utf-8"))

    # --- dangling and vague pointers -------------------------------------
    sections = index_sections(files)
    for src, section in sections.items():
        for line in pointer_lines(section):
            for m in BACKTICKED_PATH_RE.finditer(line):
                target = Path(m.group(1))
                resolved = target if target.is_absolute() else root / target
                if not resolved.is_file():
                    findings["dangling"].append(
                        f"{src.name}: `{m.group(1)}` does not exist")
            body = line.lstrip("- ").strip()
            # Independent signals: a pointer can both lack a trigger verb and
            # be too broad. Chaining them with elif hid the breadth warning on
            # any line starting with "Always".
            if not TRIGGER_RE.match(body):
                findings["vague"].append(
                    f"{src.name}: pointer states no trigger, so Claude has no "
                    f"cue to read it — {body[:70]!r}")
            if TOO_BROAD_RE.search(body):
                findings["vague"].append(
                    f"{src.name}: trigger is broad enough to fire most "
                    f"sessions; consider moving the content back into "
                    f"CLAUDE.md — {body[:70]!r}")

    # --- orphaned references ---------------------------------------------
    refs_dir = root / ".claude" / "references"
    if refs_dir.is_dir():
        pointed_at = referenced_paths(root, files)
        for ref in sorted(refs_dir.rglob("*.md")):
            if ref.name in ("INDEX.md", "_archive.md"):
                continue  # INDEX is a human catalogue; _archive is deliberately unlinked
            if ref.resolve() not in pointed_at:
                findings["orphans"].append(
                    f"{ref.relative_to(root).as_posix()}: nothing in eager "
                    f"context points here, so Claude will never read it")

    # --- drift: extracted content back in eager context -------------------
    if manifest:
        eager_blob = normalize(" ".join(
            effective_text(f.read_text(encoding="utf-8", errors="replace"))
            for f in files if f.is_file()))
        for e in manifest.get("entries", []):
            if e["verdict"] not in ("RULE", "REFERENCE", "SKILL", "NESTED", "ARCHIVE"):
                continue
            dest = e.get("dest")
            if not dest or not Path(dest).is_file():
                continue
            body = Path(dest).read_text(encoding="utf-8", errors="replace")
            _, body = split_frontmatter(body)
            sample = normalize(body)[:90]
            if len(sample) > 40 and sample in eager_blob:
                findings["drift"].append(
                    f"{e['id']} '{e['title']}': extracted to "
                    f"{Path(dest).name} but the same text is back in eager "
                    f"context — it was re-added, or never removed")

    # --- dead rules -------------------------------------------------------
    tracked = repo_files(root)
    for rules_dir in (root / ".claude" / "rules", Path.home() / ".claude" / "rules"):
        if not rules_dir.is_dir():
            continue
        for rf in sorted(rules_dir.rglob("*.md")):
            fm, _ = split_frontmatter(rf.read_text(encoding="utf-8", errors="replace"))
            for pattern in parse_paths_frontmatter(fm):
                if glob_matches(tracked, pattern) == 0:
                    findings["dead_rules"].append(
                        f"{rf.name}: `{pattern}` matches no file — never loads")

    # --- regrowth ---------------------------------------------------------
    baseline = (manifest or {}).get("eager_tokens_after")
    if baseline:
        growth = eager_now - baseline
        if growth > max(50, baseline * 0.25):
            findings["regrowth"].append(
                f"eager context is {eager_now} tokens, up from {baseline} at "
                f"the last apply (+{growth}). Worth a fresh audit.")

    total = sum(len(v) for v in findings.values())
    labels = {
        "drift": "CONTENT DRIFT", "dangling": "DANGLING POINTERS",
        "orphans": "ORPHANED REFERENCES", "dead_rules": "RULES THAT NEVER LOAD",
        "regrowth": "REGROWTH", "vague": "WEAK POINTERS",
    }
    for key in ("drift", "dangling", "dead_rules", "orphans", "regrowth", "vague"):
        if findings[key]:
            print(f"{labels[key]}")
            for item in findings[key]:
                print(f"  - {item}")
            print()

    print(f"eager context now: {eager_now} tokens"
          + (f" (was {baseline} after last apply)" if baseline else ""))
    if not total:
        print("re-audit clean")
    else:
        print(f"{total} finding(s)")

    print("\nNot measurable from disk: how often Claude actually reads each "
          "reference.\nThe WEAK POINTERS section is a proxy, not evidence — "
          "decide those yourself.")

    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps({"eager_tokens": eager_now, "findings": findings}, indent=2),
            encoding="utf-8")
    return 1 if findings["drift"] or findings["dangling"] or findings["dead_rules"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
