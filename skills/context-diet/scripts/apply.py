#!/usr/bin/env python3
"""context-diet phase 5: apply an approved plan.

Parses .claude/context-diet-plan.md, backs up every file it will touch,
performs all writes as one transaction (restoring on any failure), rewrites
the managed pointer index inside each source file, and records every block's
origin and destination in manifest.json.

Refuses to emit @path imports, and refuses to relocate a safety-critical block.
Standard library only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import time
from pathlib import Path

DECISION_RE = re.compile(r"^###\s+(B\d+)\b(.*)$")
FIELD_RE = re.compile(r"^\s*-\s*\*\*([A-Za-z_]+):\*\*\s*(.*?)\s*$")
STOP_RE = re.compile(r"^#{1,3}\s")
BARE_IMPORT_RE = re.compile(r"(?<![A-Za-z0-9_`/\\.-])@[~./\w][^\s`]*")

INDEX_START = "<!-- context-diet:index:start -->"
INDEX_END = "<!-- context-diet:index:end -->"

RELOCATING = {"RULE", "REFERENCE", "SKILL", "NESTED", "ARCHIVE"}
# POINTER removes a block and leaves a pointer, but writes nothing to the
# destination: the content is already there. This is the verdict for undoing an
# @import, where the target file exists and only the loading mechanism is wrong.
REMOVING = RELOCATING | {"DELETE", "POINTER"}
VERDICTS = REMOVING | {"KEEP", "ASK"}

REQUIRED = {
    "RULE": ("dest", "paths"),
    "REFERENCE": ("dest", "pointer"),
    "SKILL": ("name", "description"),
    "NESTED": ("dest",),
    "ARCHIVE": ("dest",),
    "POINTER": ("dest", "pointer"),
}


class PlanError(Exception):
    pass


def parse_plan(path: Path) -> dict[str, dict]:
    if not path.is_file():
        raise PlanError(f"no plan at {path} — run phases 0-4 first")
    decisions: dict[str, dict] = {}
    current: dict | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        m = DECISION_RE.match(line)
        if m:
            current = {"id": m.group(1), "title": m.group(2).strip(" ·-—")}
            decisions[m.group(1)] = current
            continue
        if current is None:
            continue
        if STOP_RE.match(line):
            current = None
            continue
        f = FIELD_RE.match(line)
        if f:
            current[f.group(1).lower()] = f.group(2).strip()
    return decisions


def validate(decisions: dict[str, dict], blocks: dict[str, dict]) -> list[str]:
    errors = []
    for bid, d in decisions.items():
        if bid not in blocks:
            errors.append(f"{bid}: not present in blocks.json")
            continue
        verdict = d.get("verdict", "").strip().upper()
        if verdict not in VERDICTS:
            errors.append(f"{bid}: verdict {verdict!r} is not one of {sorted(VERDICTS)}")
            continue
        d["verdict"] = verdict
        if d.get("critical", "no").lower().startswith("y") and verdict != "KEEP":
            errors.append(
                f"{bid}: marked critical but routed to {verdict}. Safety-critical "
                f"content must stay in root CLAUDE.md — only root survives /compact."
            )
        for key in REQUIRED.get(verdict, ()):
            if not d.get(key):
                errors.append(f"{bid}: verdict {verdict} requires '{key}'")
        pointer = d.get("pointer", "")
        if verdict in ("REFERENCE", "POINTER") and pointer:
            dest = d.get("dest", "")
            if f"`{dest}`" not in pointer:
                errors.append(
                    f"{bid}: pointer must contain `{dest}` in backticks, or the "
                    f"path is parsed as an @import and loads eagerly"
                )
        for key, value in d.items():
            if key in ("evidence", "why", "title", "id"):
                continue
            if BARE_IMPORT_RE.search(str(value)):
                errors.append(f"{bid}: field '{key}' contains a bare @path — "
                              f"imports load at launch and save nothing")
    return errors


def check_destinations(root: Path, decisions: dict[str, dict],
                       blocks: dict[str, dict]) -> list[str]:
    """A destination must never be a file we are also cutting blocks out of.

    build() stages generated content and stripped content in the same dict; if
    a destination collided with a source, the stripper would apply the original
    file's offsets to freshly generated text and cut the wrong bytes. Nested
    CLAUDE.md files are lazy and so never carry blocks, which makes this
    unreachable in normal use — but a hand-edited plan can ask for it.
    """
    # The hazard is only real for files this plan actually cuts blocks out of.
    # Merely *having* blocks is not enough: an imported doc is a source (it is
    # eager, so it gets segmented) yet is a perfectly good POINTER target when
    # no decision touches it.
    edited = {Path(blocks[bid]["file"]).resolve()
              for bid, d in decisions.items()
              if bid in blocks and d.get("verdict", "").strip().upper() in REMOVING}
    errors = []
    for bid, d in sorted(decisions.items()):
        verdict = d.get("verdict", "").strip().upper()
        dest = d.get("dest")
        if verdict == "SKILL" and d.get("name"):
            dest = f".claude/skills/{d['name']}/SKILL.md"
        if verdict not in (RELOCATING | {"POINTER"}) or not dest:
            continue
        p = Path(dest)
        p = p if p.is_absolute() else root / p
        try:
            resolved = p.resolve()
        except OSError:
            continue
        if resolved in edited:
            errors.append(
                f"{bid}: destination '{dest}' is a file this plan removes "
                f"blocks from; its offsets would be applied to generated "
                f"content. Choose a different destination")
        # POINTER writes nothing, so its target must already exist — otherwise
        # the block is removed and the pointer leads nowhere.
        if verdict == "POINTER" and not resolved.is_file():
            errors.append(
                f"{bid}: POINTER target '{dest}' does not exist. POINTER "
                f"writes no content, so the file must already be there; use "
                f"REFERENCE to move content into a new file")
    return errors


def check_freshness(state: Path, decisions: dict[str, dict],
                    blocks: dict[str, dict]) -> list[str]:
    """Block offsets are only meaningful against the exact bytes discover.py
    read. If a source file changed since — hand-edited, or already applied —
    cutting by offset would remove the wrong content."""
    try:
        inventory = json.loads((state / "inventory.json").read_text(encoding="utf-8"))
    except OSError:
        return ["inventory.json missing — re-run discover.py"]
    hashes = {f["path"]: f.get("sha256") for f in inventory.get("files", [])}
    touched = {blocks[b]["file"] for b, d in decisions.items()
               if b in blocks and d.get("verdict", "").upper() in REMOVING}
    stale = []
    for src in sorted(touched):
        p = Path(src)
        if not p.is_file():
            stale.append(f"{p.name}: no longer exists")
            continue
        # Must match discover.py's read path exactly: text mode normalises
        # CRLF to LF, so hashing raw bytes would mismatch on every Windows file.
        current = hashlib.sha256(
            p.read_text(encoding="utf-8", errors="replace").encode("utf-8")
        ).hexdigest()
        recorded = hashes.get(src)
        if not recorded:
            # Never skip the check silently: no recorded hash means the
            # inventory is from an older run and cannot vouch for the offsets.
            stale.append(f"{p.name}: inventory has no recorded hash — re-run "
                         f"discover.py before applying")
        elif current != recorded:
            stale.append(f"{p.name}: changed since discovery — re-run "
                         f"discover.py and rebuild the plan before applying")
    return stale


def commit(contents: dict[Path, str], backup_dir: Path) -> list[tuple[Path, Path]]:
    """Write every file or none of them.

    Backs up all existing targets first, then writes each via a temp file and
    an atomic replace. Any failure restores the backups, deletes files this
    call created, and removes stray temp files before re-raising.
    """
    backup_dir.mkdir(parents=True, exist_ok=True)
    backed_up: list[tuple[Path, Path]] = []
    created: list[Path] = []
    temps: list[Path] = []
    try:
        for p in contents:
            if p.is_file():
                safe = re.sub(r"[^A-Za-z0-9._-]", "_", str(p))
                dst = backup_dir / safe
                shutil.copy2(p, dst)
                backed_up.append((p, dst))
        for p, text in contents.items():
            p.parent.mkdir(parents=True, exist_ok=True)
            if not p.is_file():
                created.append(p)
            tmp = p.with_suffix(p.suffix + ".context-diet-tmp")
            temps.append(tmp)
            tmp.write_text(text, encoding="utf-8")
            tmp.replace(p)
            temps.remove(tmp)
    except Exception:
        for original, backup in backed_up:
            shutil.copy2(backup, original)
        for p in created:
            p.unlink(missing_ok=True)
        for tmp in temps:
            tmp.unlink(missing_ok=True)
        raise
    return backed_up


def strip_blocks(text: str, spans: list[tuple[int, int]]) -> str:
    for start, end in sorted(spans, reverse=True):
        text = text[:start] + text[end:]
    return re.sub(r"\n{3,}", "\n\n", text).rstrip() + "\n"


def render_index(pointers: list[str]) -> str:
    if not pointers:
        return ""
    lines = [INDEX_START, "", "## Further reading", ""]
    lines += [f"- {p}" for p in pointers]
    lines += ["", INDEX_END, ""]
    return "\n".join(lines)


def replace_index(text: str, section: str) -> str:
    if INDEX_START in text and INDEX_END in text:
        head, rest = text.split(INDEX_START, 1)
        _, tail = rest.split(INDEX_END, 1)
        merged = head.rstrip() + ("\n\n" + section.strip() + "\n" if section else "\n") + tail.lstrip("\n")
        return re.sub(r"\n{3,}", "\n\n", merged)
    if not section:
        return text
    return text.rstrip() + "\n\n" + section.strip() + "\n"


def split_globs(spec: str) -> list[str]:
    """Split a comma-separated glob list without breaking brace groups.

    `src/**/*.{ts,tsx}` is ONE pattern. Splitting naively on commas yields
    `src/**/*.{ts` and `tsx}`, which match nothing — a rule that silently
    never loads, which is the worst possible failure for this tool.
    """
    out: list[str] = []
    buf: list[str] = []
    depth = 0
    for ch in spec:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            out.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    out.append("".join(buf).strip())
    return [g for g in out if g]


def block_body(block: dict) -> str:
    """The block's text, with its own heading demoted-safe for reuse."""
    return block["text"].strip() + "\n"


def yaml_list(items: list[str]) -> str:
    return "\n".join(f'  - "{i}"' for i in items)


def build(root: Path, decisions: dict[str, dict], blocks: dict[str, dict]) -> tuple[dict[Path, str], dict]:
    writes: dict[Path, list[str]] = {}
    removals: dict[str, list[tuple[int, int]]] = {}
    pointers: dict[str, list[str]] = {}
    manifest_entries = []
    rule_paths: dict[Path, list[str]] = {}
    skill_meta: dict[Path, dict] = {}

    def target(dest: str) -> Path:
        p = Path(dest)
        return p if p.is_absolute() else (root / p)

    for bid, d in sorted(decisions.items()):
        block = blocks[bid]
        verdict = d["verdict"]
        src = block["file"]
        record = {"id": bid, "title": block["title"], "source": src,
                  "verdict": verdict, "tokens": block["tokens"],
                  "start": block["start"], "end": block["end"]}

        if verdict in REMOVING:
            removals.setdefault(src, []).append((block["start"], block["end"]))

        if verdict == "RULE":
            dest = target(d["dest"])
            globs = split_globs(d["paths"])
            rule_paths.setdefault(dest, [])
            rule_paths[dest] += [g for g in globs if g not in rule_paths[dest]]
            writes.setdefault(dest, []).append(block_body(block))
            record["dest"] = str(dest)
            record["paths"] = globs
        elif verdict == "REFERENCE":
            dest = target(d["dest"])
            writes.setdefault(dest, []).append(block_body(block))
            pointers.setdefault(src, []).append(d["pointer"])
            record["dest"] = str(dest)
            record["pointer"] = d["pointer"]
        elif verdict == "SKILL":
            dest = root / ".claude" / "skills" / d["name"] / "SKILL.md"
            skill_meta[dest] = {"name": d["name"], "description": d["description"]}
            writes.setdefault(dest, []).append(block_body(block))
            record["dest"] = str(dest)
        elif verdict == "NESTED":
            dest = target(d["dest"])
            writes.setdefault(dest, []).append(block_body(block))
            record["dest"] = str(dest)
        elif verdict == "ARCHIVE":
            dest = target(d["dest"])
            writes.setdefault(dest, []).append(block_body(block))
            record["dest"] = str(dest)
        elif verdict == "POINTER":
            # The destination already holds the content — usually because the
            # block was an @import. Remove the block, keep a pointer, write
            # nothing. This is the cheapest possible extraction.
            dest = target(d["dest"])
            pointers.setdefault(src, []).append(d["pointer"])
            record["dest"] = str(dest)
            record["pointer"] = d["pointer"]
            record["wrote_content"] = False
        elif verdict == "DELETE":
            record["dest"] = None
            record["deleted_text"] = block["text"]

        record["why"] = d.get("why", "")
        manifest_entries.append(record)

    contents: dict[Path, str] = {}

    for dest, parts in writes.items():
        header = ""
        if dest in rule_paths:
            header = "---\npaths:\n" + yaml_list(rule_paths[dest]) + "\n---\n\n"
        elif dest in skill_meta:
            meta = skill_meta[dest]
            desc = meta["description"].replace("\n", " ")
            header = f"---\nname: {meta['name']}\ndescription: {desc}\n---\n\n"
        existing = ""
        if dest.is_file():
            prior = dest.read_text(encoding="utf-8")
            if header and prior.startswith("---"):
                # Preserve the file, replace only our generated frontmatter.
                prior = prior.split("---", 2)[-1].lstrip("\n")
            existing = prior.rstrip() + "\n\n"
        body = existing + "\n\n".join(p.strip() for p in parts) + "\n"
        trailer = "<!-- extracted by context-diet -->"
        if trailer not in body:
            body += f"\n{trailer}\n"
        contents[dest] = header + body

    for src, spans in removals.items():
        p = Path(src)
        text = contents.get(p) or p.read_text(encoding="utf-8")
        text = strip_blocks(text, spans)
        contents[p] = text

    for src, ptrs in pointers.items():
        p = Path(src)
        text = contents.get(p) or p.read_text(encoding="utf-8")
        contents[p] = replace_index(text, render_index(ptrs))

    refs = sorted({Path(e["dest"]) for e in manifest_entries
                   if e["verdict"] in ("REFERENCE", "ARCHIVE", "POINTER")
                   and e.get("dest")})
    if refs:
        idx = root / ".claude" / "references" / "INDEX.md"
        lines = ["# Reference index", "",
                 "<!-- generated by context-diet; CLAUDE.md carries the pointers Claude uses -->",
                 ""]
        for r in refs:
            titles = [e["title"] for e in manifest_entries if e.get("dest") == str(r)]
            try:
                rel = r.relative_to(root).as_posix()
            except ValueError:
                rel = r.as_posix()
            lines.append(f"- `{rel}` — {', '.join(titles)}")
        contents[idx] = "\n".join(lines) + "\n"

    manifest = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "root": str(root),
        "entries": manifest_entries,
        "written": [str(p) for p in sorted(contents)],
    }
    return contents, manifest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".")
    ap.add_argument("--plan", default=None)
    ap.add_argument("--state", default=None,
                    help="state dir from discover.py --json-out "
                         "(default <root>/.claude/.context-diet)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    state = Path(args.state) if args.state else root / ".claude" / ".context-diet"
    plan_path = Path(args.plan) if args.plan else root / ".claude" / "context-diet-plan.md"

    try:
        blocks = json.loads((state / "blocks.json").read_text(encoding="utf-8"))
    except OSError:
        print("error: blocks.json missing — run discover.py first", file=sys.stderr)
        return 2

    try:
        decisions = parse_plan(plan_path)
    except PlanError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    if not decisions:
        print("error: plan contains no '### B..' decisions", file=sys.stderr)
        return 2

    errors = (check_freshness(state, decisions, blocks)
              + check_destinations(root, decisions, blocks)
              + validate(decisions, blocks))
    if errors:
        print("plan rejected:\n", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    unresolved = [b for b, d in decisions.items() if d["verdict"] == "ASK"]
    contents, manifest = build(root, decisions, blocks)

    if args.dry_run:
        for p, c in sorted(contents.items()):
            print(f"--- {p} ({len(c)} bytes) ---")
        print(f"\n{len(contents)} files would be written")
        return 0

    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup_dir = state / "backups" / stamp

    try:
        commit(contents, backup_dir)
    except Exception as exc:
        print(f"error: apply failed and was rolled back: {exc}", file=sys.stderr)
        return 1

    manifest["backup_dir"] = str(backup_dir)
    (state / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    counts: dict[str, int] = {}
    for e in manifest["entries"]:
        counts[e["verdict"]] = counts.get(e["verdict"], 0) + 1
    print(f"applied {len(manifest['entries'])} decisions across {len(contents)} files")
    for v, n in sorted(counts.items()):
        print(f"  {v:<10} {n}")
    print(f"backups: {backup_dir}")
    if unresolved:
        print(f"\nunresolved (ASK, left in place): {', '.join(sorted(unresolved))}")
    print("\nnow run verify.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
