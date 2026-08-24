#!/usr/bin/env python3
"""context-diet phase 6: prove the apply was correct.

Checks, in order of how badly each failure would bite:

  1. Content accounting  - every block is in its declared destination, or on
                           the approved deletion list. Nothing vanished.
  2. Glob reachability   - every `paths:` pattern matches at least one real
                           file. A glob matching nothing is a rule that never
                           loads: silent, total failure.
  3. Pointer resolution  - every path named in the managed index exists.
  4. Skill validity      - every generated SKILL.md has name + description.
  5. No new @imports     - nothing was introduced that loads eagerly.
  6. Measurement         - eager tokens before vs after, measured not claimed.

Exit code is non-zero if any check fails. Standard library only.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from discover import (  # noqa: E402
    IMPORT_RE, SKIP_DIRS, discover, effective_text, estimate_tokens,
    mask_code, parse_paths_frontmatter, split_frontmatter,
)

BACKTICKED_PATH_RE = re.compile(r"`([^`\n]+\.(?:md|markdown))`")
INDEX_START = "<!-- context-diet:index:start -->"
INDEX_END = "<!-- context-diet:index:end -->"


class Result:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.warnings: list[str] = []
        self.passes: list[str] = []

    def fail(self, msg: str) -> None:
        self.failures.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def ok(self, msg: str) -> None:
        self.passes.append(msg)


def expand_braces(pattern: str) -> list[str]:
    m = re.search(r"\{([^{}]*)\}", pattern)
    if not m:
        return [pattern]
    out = []
    for option in m.group(1).split(","):
        out += expand_braces(pattern[:m.start()] + option + pattern[m.end():])
    return out


def glob_to_regex(pattern: str) -> re.Pattern[str]:
    """Translate a rules-style glob to a path-aware regex.

    fnmatch is deliberately not used: its `*` matches across `/`, so
    `src/api/**/*.ts` would fail to match `src/api/users.ts`. Here `**`
    spans directories, `*` does not, matching real glob semantics.
    """
    out, i, n = [], 0, len(pattern)
    while i < n:
        c = pattern[i]
        if pattern.startswith("**/", i):
            out.append("(?:[^/]+/)*")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif c == "*":
            out.append("[^/]*")
            i += 1
        elif c == "?":
            out.append("[^/]")
            i += 1
        elif c == "[":
            close = pattern.find("]", i + 1)
            if close == -1:  # unclosed bracket: matches nothing, per glob rules
                return re.compile(r"(?!)")
            body = pattern[i + 1:close].replace("\\", "\\\\")
            if body.startswith("!"):
                body = "^" + body[1:]
            out.append(f"[{body}]")
            i = close + 1
        elif c == "\\" and i + 1 < n:
            out.append(re.escape(pattern[i + 1]))
            i += 2
        else:
            out.append(re.escape(c))
            i += 1
    return re.compile("".join(out) + r"\Z")


def repo_files(root: Path) -> list[str]:
    """Relative posix paths of candidate files, vendor directories excluded."""
    files = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if set(rel.parts[:-1]) & SKIP_DIRS or any(p.startswith(".") for p in rel.parts[:-1]):
            continue
        files.append(rel.as_posix())
    return files


def glob_matches(files: list[str], pattern: str, limit: int = 1) -> int:
    """Count files matching a rules-style glob."""
    count = 0
    for expanded in expand_braces(pattern):
        rx = glob_to_regex(expanded.replace("\\", "/").lstrip("./"))
        for rel in files:
            if rx.match(rel):
                count += 1
                if count >= limit:
                    return count
    return count


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def check_accounting(root: Path, manifest: dict, res: Result) -> None:
    cache: dict[Path, str] = {}

    def body(path: Path) -> str:
        if path not in cache:
            cache[path] = normalize(path.read_text(encoding="utf-8")) if path.is_file() else ""
        return cache[path]

    for e in manifest["entries"]:
        bid, verdict = e["id"], e["verdict"]
        source = Path(e["source"])
        excerpt = normalize(e.get("deleted_text", ""))[:120]

        if verdict in ("KEEP", "ASK"):
            continue
        if verdict == "DELETE":
            if excerpt and excerpt in body(source):
                res.fail(f"{bid}: marked DELETE but still present in {source.name}")
            continue
        dest = e.get("dest")
        if not dest:
            res.fail(f"{bid}: verdict {verdict} recorded no destination")
            continue
        dp = Path(dest)
        if not dp.is_file():
            res.fail(f"{bid}: destination {dest} does not exist")
            continue
        if e.get("wrote_content") is False:
            # POINTER moves no content by design: the destination already held
            # it. Existence of the target is the only thing to confirm.
            continue
        # A content sample proves the move, without demanding byte equality
        # (frontmatter and headers are legitimately added on the way out).
        sample = normalize(e.get("title", ""))
        if sample and sample not in body(dp):
            res.warn(f"{bid}: could not confirm '{sample[:50]}' inside {dp.name}")
    res.ok(f"accounting checked for {len(manifest['entries'])} blocks")


def check_globs(root: Path, res: Result, home: Path | None = None) -> None:
    # `home` is injectable so tests do not depend on the developer's real
    # ~/.claude, and so a machine with user-scope rules cannot skew results.
    home = home or Path.home()
    checked = 0
    files = repo_files(root)
    for rules_dir in (root / ".claude" / "rules", home / ".claude" / "rules"):
        if not rules_dir.is_dir():
            continue
        for rf in sorted(rules_dir.rglob("*.md")):
            fm, _ = split_frontmatter(rf.read_text(encoding="utf-8", errors="replace"))
            for pattern in parse_paths_frontmatter(fm):
                checked += 1
                if "[" in pattern and not re.search(r"\[[^\]]*\]", pattern):
                    res.fail(f"{rf.name}: pattern '{pattern}' has an unclosed "
                             f"bracket expression and matches nothing")
                    continue
                hits = glob_matches(files, pattern, limit=len(files) or 1)
                if hits == 0:
                    res.fail(f"{rf.name}: pattern '{pattern}' matches no file — "
                             f"this rule will never load")
                elif files and hits / len(files) > 0.6:
                    res.warn(f"{rf.name}: pattern '{pattern}' matches {hits}/"
                             f"{len(files)} files; scoping saves little here")
    res.ok(f"{checked} path globs checked for reachability")


def check_pointers(root: Path, res: Result, home: Path | None = None) -> None:
    home = home or Path.home()
    checked = 0
    for md in list(root.rglob("CLAUDE.md")) + [home / ".claude" / "CLAUDE.md"]:
        if not md.is_file():
            continue
        text = md.read_text(encoding="utf-8", errors="replace")
        if INDEX_START not in text:
            continue
        section = text.split(INDEX_START, 1)[1].split(INDEX_END, 1)[0]
        for m in BACKTICKED_PATH_RE.finditer(section):
            checked += 1
            candidate = Path(m.group(1))
            resolved = candidate if candidate.is_absolute() else root / candidate
            if not resolved.is_file():
                res.fail(f"{md.name}: pointer target `{m.group(1)}` does not exist")
        if not BACKTICKED_PATH_RE.search(section) and section.strip():
            res.warn(f"{md.name}: index section has no backticked .md path — "
                     f"pointers may be unusable")
    res.ok(f"{checked} pointer targets resolved")


def check_skills(root: Path, res: Result) -> None:
    checked = 0
    for sf in sorted((root / ".claude" / "skills").glob("*/SKILL.md")):
        checked += 1
        fm, body = split_frontmatter(sf.read_text(encoding="utf-8", errors="replace"))
        if not re.search(r"^\s*name\s*:", fm, re.MULTILINE):
            res.fail(f"{sf.parent.name}: SKILL.md has no 'name' in frontmatter")
        desc = re.search(r"^\s*description\s*:\s*(.+)$", fm, re.MULTILINE)
        if not desc:
            res.fail(f"{sf.parent.name}: SKILL.md has no 'description' — it will never trigger")
        elif len(desc.group(1).strip()) < 40:
            res.warn(f"{sf.parent.name}: description is very short; triggering "
                     f"depends entirely on it")
        if not body.strip():
            res.fail(f"{sf.parent.name}: SKILL.md body is empty")
    res.ok(f"{checked} project skills validated")


def check_no_imports(root: Path, res: Result, home: Path | None = None) -> None:
    home = home or Path.home()
    found = 0
    targets = [p for p in root.rglob("CLAUDE.md")
               if not (set(p.relative_to(root).parts) & SKIP_DIRS)]
    targets.append(home / ".claude" / "CLAUDE.md")
    for md in targets:
        if not md.is_file():
            continue
        text = md.read_text(encoding="utf-8", errors="replace")
        for m in IMPORT_RE.finditer(mask_code(text)):
            raw = m.group(1)
            target = Path(raw).expanduser()
            if not target.is_absolute():
                target = md.parent / target
            if target.is_file():
                # Resolves to a real file, so Claude Code will expand it at
                # launch. This is the failure the whole tool exists to prevent.
                found += 1
                res.fail(f"{md.name}: contains @{raw} — imports load at "
                         f"launch and save no context")
            elif "/" in raw or raw.endswith(".md"):
                # Path-shaped but resolves to nothing: a typo'd import, worth
                # flagging but not a context cost.
                res.warn(f"{md.name}: '@{raw}' looks like an import but "
                         f"resolves to nothing — typo, or intended as text?")
            # Anything else (@fileoverview, @param, @returns) is a JSDoc tag
            # in prose. It imports nothing and is not worth reporting.
    if not found:
        res.ok("no @path imports present")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    state = root / ".claude" / ".context-diet"

    res = Result()

    try:
        manifest = json.loads((state / "manifest.json").read_text(encoding="utf-8"))
    except OSError:
        print("error: manifest.json missing — run apply.py first", file=sys.stderr)
        return 2

    before = None
    try:
        inv = json.loads((state / "inventory.json").read_text(encoding="utf-8"))
        before = inv["totals"]["eager_tokens"]
    except (OSError, KeyError):
        pass

    check_accounting(root, manifest, res)
    check_globs(root, res)
    check_pointers(root, res)
    check_skills(root, res)
    check_no_imports(root, res)

    after_inv, _ = discover(root)
    after = after_inv["totals"]["eager_tokens"]

    # Record the post-apply figure so reaudit.py can detect regrowth later.
    manifest["eager_tokens_after"] = after
    if before is not None:
        manifest["eager_tokens_before"] = before
    try:
        (state / "manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8")
    except OSError:
        pass

    for p in res.passes:
        print(f"  ok    {p}")
    for w in res.warnings:
        print(f"  warn  {w}")
    for f in res.failures:
        print(f"  FAIL  {f}")

    print()
    if before is not None:
        saved = before - after
        pct = (saved / before * 100) if before else 0
        print(f"eager context: {before} -> {after} tokens  "
              f"({-saved:+d}, {-pct:+.1f}%)")
    else:
        print(f"eager context: {after} tokens")
    print(f"eager files: {after_inv['totals']['eager_files']}  "
          f"lazy files: {after_inv['totals']['lazy_files']}")

    if res.failures:
        print(f"\n{len(res.failures)} check(s) failed. "
              f"Backups: {manifest.get('backup_dir', state / 'backups')}")
        return 1
    print("\nall checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
