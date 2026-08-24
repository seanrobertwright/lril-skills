#!/usr/bin/env python3
"""context-diet phase 0: inventory every file that can enter Claude's context.

Finds each instruction source, classifies it as eager (paid for on every
session) or lazy (loaded on demand), measures it, and segments the eager
markdown into offset-addressed blocks so later phases can prove nothing was
lost.

Writes inventory.json and blocks.json. Standard library only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

# --------------------------------------------------------------------------
# markdown utilities
# --------------------------------------------------------------------------

FENCE_RE = re.compile(r"^(\s*)(`{3,}|~{3,})")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
CODE_SPAN_RE = re.compile(r"`[^`\n]*`")
# An @import: an @ that starts a token, followed by a path-ish run.
IMPORT_RE = re.compile(r"(?<![A-Za-z0-9_`/\\.-])@([~./\w][^\s`\"'<>()\[\]]*)")

SKIP_DIRS = {
    ".git", "node_modules", "dist", "build", "out", "target", ".next",
    ".venv", "venv", "__pycache__", ".mypy_cache", ".pytest_cache",
    ".tox", "vendor", ".cache", "coverage", ".turbo", ".svelte-kit",
}


def estimate_tokens(text: str) -> int:
    """Rough token estimate. Deliberately crude and consistently applied:
    what matters is the before/after delta, not absolute accuracy."""
    if not text.strip():
        return 0
    return max(1, math.ceil(len(text) / 4))


def split_frontmatter(text: str) -> tuple[str, str]:
    """Return (frontmatter_body, rest). Frontmatter is stripped before the
    content is loaded, so it does not count toward context cost."""
    if not text.startswith("---"):
        return "", text
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return "", text
    for i in range(1, len(lines)):
        if lines[i].strip() in ("---", "..."):
            return "".join(lines[1:i]), "".join(lines[i + 1:])
    return "", text


def effective_text(text: str) -> str:
    """What actually reaches the context window: frontmatter and block-level
    HTML comments are stripped before injection."""
    _, body = split_frontmatter(text)
    return HTML_COMMENT_RE.sub("", body)


def blank_line(line: str) -> str:
    """Replace every character except newlines with a space, preserving length
    so that offsets into the masked text still index the original."""
    return re.sub(r"[^\n]", " ", line)


def mask_code(text: str) -> str:
    """Blank out fenced blocks and code spans, preserving offsets, so heading
    detection and import scanning do not fire on documented examples.

    Fence matching follows CommonMark: a closing fence must use the same
    character, be at least as long as the opening fence, and contain nothing
    but that character. Treating any ``` as a closer silently inverts the
    fence state on files that use ````-fences to show markdown inside markdown
    -- after the first such block every real heading is masked, collapsing the
    rest of the file into a single unusable block.
    """
    out = []
    in_fence = False
    fence_char = ""
    fence_len = 0
    for line in text.splitlines(keepends=True):
        m = FENCE_RE.match(line)
        if m:
            marker = m.group(2)
            if not in_fence:
                in_fence, fence_char, fence_len = True, marker[0], len(marker)
                out.append(blank_line(line))
                continue
            stripped = line.strip()
            if (marker[0] == fence_char and len(marker) >= fence_len
                    and set(stripped) == {fence_char}):
                in_fence = False
                out.append(blank_line(line))
                continue
        out.append(blank_line(line) if in_fence else line)
    masked = "".join(out)
    return CODE_SPAN_RE.sub(lambda m: " " * len(m.group(0)), masked)


def parse_paths_frontmatter(fm: str) -> list[str]:
    """Extract a rules file's `paths:` globs without a YAML dependency."""
    if not fm:
        return []
    lines = fm.splitlines()
    for i, line in enumerate(lines):
        if not re.match(r"^\s*paths\s*:", line):
            continue
        inline = line.split(":", 1)[1].strip()
        if inline.startswith("["):
            return [p.strip().strip("\"'") for p in
                    inline.strip("[]").split(",") if p.strip()]
        globs = []
        for nxt in lines[i + 1:]:
            if not nxt.strip():
                continue
            m = re.match(r"^\s*-\s*(.+?)\s*$", nxt)
            if not m:
                break
            globs.append(m.group(1).strip().strip("\"'"))
        return globs
    return []


def parse_frontmatter_field(fm: str, key: str) -> str:
    if not fm:
        return ""
    m = re.search(rf"^\s*{re.escape(key)}\s*:\s*(.+?)\s*$", fm, re.MULTILINE)
    return m.group(1).strip().strip("\"'") if m else ""


def segment(text: str) -> list[dict]:
    """Split markdown into blocks whose offsets tile the file completely.

    Complete tiling is the point: it makes post-apply content accounting
    arithmetic rather than judgement.
    """
    masked = mask_code(text)
    starts: list[tuple[int, int, str]] = []  # (offset, level, title)
    offset = 0
    for line in masked.splitlines(keepends=True):
        m = HEADING_RE.match(line)
        if m:
            starts.append((offset, len(m.group(1)), m.group(2)))
        offset += len(line)

    bounds: list[tuple[int, int, int, str]] = []
    if len(starts) >= 2:
        if starts[0][0] > 0:
            bounds.append((0, starts[0][0], 0, "(preamble)"))
        for i, (off, level, title) in enumerate(starts):
            end = starts[i + 1][0] if i + 1 < len(starts) else len(text)
            bounds.append((off, end, level, title))
    else:
        # No usable heading structure: fall back to blank-line-separated chunks.
        pos, chunk_start = 0, 0
        blanks = 0
        for line in text.splitlines(keepends=True):
            if line.strip():
                if blanks and pos > chunk_start:
                    bounds.append((chunk_start, pos, 0, ""))
                    chunk_start = pos
                blanks = 0
            else:
                blanks += 1
            pos += len(line)
        if chunk_start < len(text):
            bounds.append((chunk_start, len(text), 0, ""))
        if not bounds:
            bounds = [(0, len(text), 0, "")]

    blocks = []
    for start, end, level, title in bounds:
        raw = text[start:end]
        if not raw.strip():
            continue
        eff = effective_text(raw) if start > 0 else effective_text(raw)
        if not title:
            first = next((ln.strip() for ln in raw.splitlines() if ln.strip()), "")
            title = (first[:60] + "…") if len(first) > 60 else first
        blocks.append({
            "start": start,
            "end": end,
            "level": level,
            "title": title.lstrip("# ").strip(),
            "lines": raw.count("\n") + (0 if raw.endswith("\n") else 1),
            "tokens": estimate_tokens(eff),
            "text": raw,
        })
    return blocks


# --------------------------------------------------------------------------
# discovery
# --------------------------------------------------------------------------

def managed_policy_path() -> Path | None:
    if sys.platform == "win32":
        return Path(r"C:\Program Files\ClaudeCode\CLAUDE.md")
    if sys.platform == "darwin":
        return Path("/Library/Application Support/ClaudeCode/CLAUDE.md")
    return Path("/etc/claude-code/CLAUDE.md")


def git_root(root: Path) -> Path | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=10,
        )
        if out.returncode == 0 and out.stdout.strip():
            return Path(out.stdout.strip())
    except Exception:
        pass
    return None


def tracked_file_count(root: Path) -> int | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "ls-files"],
            capture_output=True, text=True, timeout=30,
        )
        if out.returncode == 0:
            return len([l for l in out.stdout.splitlines() if l.strip()])
    except Exception:
        pass
    return None


def auto_memory_index(root: Path, home: Path | None = None) -> Path | None:
    base = (home or Path.home()) / ".claude" / "projects"
    if not base.is_dir():
        return None
    for candidate_root in filter(None, [git_root(root), root]):
        slug = re.sub(r"[^A-Za-z0-9]", "-", str(candidate_root))
        p = base / slug / "memory" / "MEMORY.md"
        if p.is_file():
            return p
    return None


def resolve_imports(path: Path, depth: int, seen: set[Path]) -> list[dict]:
    """Follow @path imports the way Claude Code does: expanded at launch,
    max four hops, relative to the containing file."""
    if depth > 4:
        return []
    found = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    for m in IMPORT_RE.finditer(mask_code(text)):
        raw = m.group(1)
        target = Path(os.path.expanduser(raw))
        if not target.is_absolute():
            target = (path.parent / target).resolve()
        if target in seen or not target.is_file():
            continue
        seen.add(target)
        found.append({"path": target, "depth": depth, "via": path, "raw": raw})
        found.extend(resolve_imports(target, depth + 1, seen))
    return found


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def entry(path: Path, kind: str, eager: bool, root: Path, **extra) -> dict:
    text = read(path)
    eff = effective_text(text)
    rec = {
        "path": str(path),
        "posix": path.as_posix(),
        "kind": kind,
        "eager": eager,
        # Block offsets are only valid against this exact content. apply.py
        # refuses to cut a file whose hash has moved on.
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "bytes": len(text.encode("utf-8")),
        "lines": text.count("\n") + (1 if text and not text.endswith("\n") else 0),
        "raw_tokens": estimate_tokens(text),
        "tokens": estimate_tokens(eff),
    }
    try:
        rec["relative"] = str(path.relative_to(root))
    except ValueError:
        rec["relative"] = str(path)
    rec.update(extra)
    return rec


def discover(root: Path, home: Path | None = None,
             managed: Path | None = None) -> dict:
    # `home` and `managed` are injectable so tests can build a complete,
    # deterministic instruction tree instead of depending on whatever the
    # developer happens to have in ~/.claude and the OS policy path.
    root = root.resolve()
    home = home or Path.home()
    files: list[dict] = []
    seen_paths: set[Path] = set()

    def add(path: Path, kind: str, eager: bool, **extra) -> dict | None:
        rp = path.resolve()
        if rp in seen_paths or not rp.is_file():
            return None
        seen_paths.add(rp)
        rec = entry(rp, kind, eager, root, **extra)
        files.append(rec)
        return rec

    mp = managed if managed is not None else managed_policy_path()
    if mp:
        add(mp, "managed-policy", True, note="cannot be excluded by settings")

    add(home / ".claude" / "CLAUDE.md", "user-claude-md", True)

    for rules_dir, scope in ((home / ".claude" / "rules", "user-rule"),
                             (root / ".claude" / "rules", "project-rule")):
        if rules_dir.is_dir():
            for rf in sorted(rules_dir.rglob("*.md")):
                fm, _ = split_frontmatter(read(rf))
                globs = parse_paths_frontmatter(fm)
                add(rf, scope, eager=not globs, paths=globs)

    # Ancestors load in full at launch; the working directory itself included.
    chain = [root, *root.parents]
    for d in reversed(chain):
        add(d / "CLAUDE.md", "ancestor-claude-md" if d != root else "project-claude-md", True)
        add(d / ".claude" / "CLAUDE.md", "project-claude-md", True)
        add(d / "CLAUDE.local.md", "local-claude-md", True)

    # Subdirectory CLAUDE.md files load only when Claude reads files there.
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        p = Path(dirpath)
        if p == root:
            continue
        for name in ("CLAUDE.md", "CLAUDE.local.md"):
            if name in filenames:
                add(p / name, "nested-claude-md", False)

    # Imports are expanded at launch: they cost exactly what their content costs.
    import_seen: set[Path] = set()
    for rec in list(files):
        if not rec["eager"]:
            continue
        for imp in resolve_imports(Path(rec["path"]), 1, import_seen):
            add(imp["path"], "import", True,
                imported_by=str(imp["via"]), depth=imp["depth"], raw=imp["raw"])

    mem = auto_memory_index(root, home)
    if mem:
        rec = add(mem, "auto-memory-index", True)
        if rec:
            body = effective_text(read(mem))
            capped = "\n".join(body.splitlines()[:200])[:25_600]
            rec["tokens"] = estimate_tokens(capped)
            rec["note"] = "only first 200 lines / 25KB load"
            rec["truncated"] = len(body) > len(capped)

    skills = []
    for skills_dir, scope in ((home / ".claude" / "skills", "user"),
                              (root / ".claude" / "skills", "project")):
        if not skills_dir.is_dir():
            continue
        for sf in sorted(skills_dir.glob("*/SKILL.md")):
            fm, _ = split_frontmatter(read(sf))
            skills.append({
                "path": str(sf),
                "scope": scope,
                "name": parse_frontmatter_field(fm, "name") or sf.parent.name,
                "description": parse_frontmatter_field(fm, "description"),
            })

    blocks = {}
    counter = 0
    for rec in files:
        if not rec["eager"] or rec["kind"] == "managed-policy":
            continue
        text = read(Path(rec["path"]))
        for blk in segment(text):
            counter += 1
            bid = f"B{counter:02d}"
            blocks[bid] = {"id": bid, "file": rec["path"],
                           "relative": rec["relative"], **blk}

    eager = [f for f in files if f["eager"]]
    lazy = [f for f in files if not f["eager"]]
    return {
        "root": str(root),
        "git_root": str(git_root(root) or ""),
        "tracked_files": tracked_file_count(root),
        "files": files,
        "skills": skills,
        "totals": {
            "eager_files": len(eager),
            "eager_tokens": sum(f["tokens"] for f in eager),
            "eager_lines": sum(f["lines"] for f in eager),
            "lazy_files": len(lazy),
            "blocks": len(blocks),
            "imports": len([f for f in files if f["kind"] == "import"]),
        },
    }, blocks


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".", help="project directory")
    ap.add_argument("--json-out", default=None,
                    help="output dir (default <root>/.claude/.context-diet)")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2

    inventory, blocks = discover(root)
    out_dir = Path(args.json_out) if args.json_out else root / ".claude" / ".context-diet"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "inventory.json").write_text(
        json.dumps(inventory, indent=2), encoding="utf-8")
    (out_dir / "blocks.json").write_text(
        json.dumps(blocks, indent=2), encoding="utf-8")

    t = inventory["totals"]
    print(f"root: {root}")
    print(f"tracked files: {inventory['tracked_files'] if inventory['tracked_files'] is not None else 'n/a (not a git repo)'}")
    print()
    print(f"EAGER  {t['eager_files']} files  {t['eager_lines']} lines  ~{t['eager_tokens']} tokens  <- paid every session")
    print(f"LAZY   {t['lazy_files']} files (load on demand)")
    print(f"BLOCKS {t['blocks']} addressable")
    if t["imports"]:
        print(f"\n!! {t['imports']} @import(s) found. These load at launch and save nothing.")
    print()
    for f in sorted(inventory["files"], key=lambda x: -x["tokens"]):
        flag = "EAGER" if f["eager"] else "lazy "
        extra = ""
        if f.get("paths"):
            extra = f"  paths={','.join(f['paths'])}"
        elif f.get("imported_by"):
            extra = f"  <- imported by {Path(f['imported_by']).name}"
        elif f.get("note"):
            extra = f"  ({f['note']})"
        print(f"  {flag} {f['tokens']:>6} tok  {f['kind']:<18} {f['relative']}{extra}")
    print(f"\n{len(inventory['skills'])} skills visible (checked for duplicate coverage)")
    print(f"\nwrote {out_dir / 'inventory.json'} and {out_dir / 'blocks.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
