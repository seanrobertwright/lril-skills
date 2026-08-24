#!/usr/bin/env python3
"""Self-tests for context-diet tooling. Run: python scripts/selftest.py

Covers the behaviours whose silent failure would be worst: block tiling
(content accounting depends on it), import detection (the whole premise),
glob translation (a wrong glob means a rule that never loads), and plan
parsing (garbage in, files rewritten).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import apply as A  # noqa: E402
import discover as D  # noqa: E402
import verify as V  # noqa: E402

FAILED: list[str] = []


def check(name: str, got, want) -> None:
    if got != want:
        FAILED.append(f"{name}\n      got:  {got!r}\n      want: {want!r}")


def truthy(name: str, got) -> None:
    if not got:
        FAILED.append(f"{name}\n      got falsy: {got!r}")


# ---------------------------------------------------------------- segmentation

DOC = """# Title

intro text

## One

alpha

## Two

beta
"""

blocks = D.segment(DOC)
check("segment: block count", len(blocks), 3)
check("segment: titles", [b["title"] for b in blocks], ["Title", "One", "Two"])
check("segment: tiles from zero", blocks[0]["start"], 0)
check("segment: tiles to end", blocks[-1]["end"], len(DOC))
for i in range(len(blocks) - 1):
    check(f"segment: contiguous {i}", blocks[i]["end"], blocks[i + 1]["start"])
check("segment: reassembles exactly",
      "".join(DOC[b["start"]:b["end"]] for b in blocks), DOC)

NO_HEADINGS = "first para\nstill first\n\nsecond para\n\nthird para\n"
check("segment: heading-free fallback", len(D.segment(NO_HEADINGS)), 3)

FENCED = "# A\n\n```\n# not a heading\n```\n\n## B\n\nx\n"
check("segment: ignores headings in fences",
      [b["title"] for b in D.segment(FENCED)], ["A", "B"])

# Regression: a ````-fence containing a ```-fence. Closing on any ``` inverts
# the fence state and swallows every heading in the rest of the file. Found on
# a real 1,049-line CLAUDE.md where it collapsed 5,161 tokens into one block.
NESTED_FENCE = (
    "# A\n\n"
    "````markdown\n"
    "```typescript\n"
    "const x = 1;\n"
    "```\n"
    "````\n\n"
    "## B\n\nreal content\n\n"
    "## C\n\nmore\n"
)
check("segment: ````-fence containing ```-fence keeps later headings",
      [b["title"] for b in D.segment(NESTED_FENCE)], ["A", "B", "C"])
check("segment: inner fence stays masked",
      "const x = 1" in D.mask_code(NESTED_FENCE), False)
check("segment: masking preserves offsets exactly",
      len(D.mask_code(NESTED_FENCE)), len(NESTED_FENCE))
check("segment: text after a nested fence is not masked",
      "real content" in D.mask_code(NESTED_FENCE), True)

# A ```-fence must NOT be closed by a longer ````-line that opens a new block.
UNEVEN = "# A\n\n```\ncode\n```\n\n## B\n\n````\nmore code\n````\n\n## C\n\nx\n"
check("segment: uneven fence lengths still segment correctly",
      [b["title"] for b in D.segment(UNEVEN)], ["A", "B", "C"])


# -------------------------------------------------------------------- imports

def imports(text: str) -> list[str]:
    return [m.group(1) for m in D.IMPORT_RE.finditer(D.mask_code(text))]


check("import: plain path", imports("see @docs/git.md here"), ["docs/git.md"])
check("import: home path", imports("- @~/.claude/x.md"), ["~/.claude/x.md"])
check("import: backticked is inert", imports("see `@README` here"), [])
check("import: fenced is inert", imports("```\n@docs/x.md\n```\n"), [])
check("import: email is not an import", imports("mail a@b.com now"), [])
check("import: bare word", imports("@AGENTS.md"), ["AGENTS.md"])


# ----------------------------------------------------------------- frontmatter

FM = '---\npaths:\n  - "src/**/*.ts"\n  - lib/**/*.ts\n---\n\nbody\n'
fm, body = D.split_frontmatter(FM)
check("frontmatter: body", body.strip(), "body")
check("frontmatter: paths", D.parse_paths_frontmatter(fm),
      ["src/**/*.ts", "lib/**/*.ts"])
inline_fm, _ = D.split_frontmatter('---\npaths: ["a/**", "b/*.md"]\n---\nx\n')
check("frontmatter: inline paths", D.parse_paths_frontmatter(inline_fm),
      ["a/**", "b/*.md"])
check("frontmatter: absent", D.parse_paths_frontmatter(""), [])


# ---------------------------------------------------------- effective content

check("effective: strips html comments",
      D.effective_text("a\n<!-- note -->\nb\n").strip(), "a\n\nb".strip())
check("effective: strips frontmatter",
      D.effective_text("---\nname: x\n---\nbody\n").strip(), "body")


# ----------------------------------------------------------------------- globs

FILES = [
    "src/api/users.ts", "src/api/v2/orders.ts", "src/db/index.ts",
    "tests/users.test.ts", "README.md", "docs/guide.md", "app.tsx",
]


def matches(pattern: str) -> list[str]:
    rx = V.glob_to_regex(pattern)
    return [f for f in FILES if rx.match(f)]


check("glob: ** spans zero dirs", matches("src/api/**/*.ts"),
      ["src/api/users.ts", "src/api/v2/orders.ts"])
check("glob: leading **", matches("**/*.test.ts"), ["tests/users.test.ts"])
check("glob: bare *.md is root only", matches("*.md"), ["README.md"])
check("glob: * does not cross slash", matches("src/*.ts"), [])
check("glob: ** alone", len(matches("src/**")), 3)
check("glob: unclosed bracket matches nothing", matches("photos [2024/**"), [])
check("glob: braces expand",
      V.glob_matches(FILES, "*.{md,tsx}", limit=99), 2)
check("glob: no match returns zero",
      V.glob_matches(FILES, "nowhere/**/*.rs"), 0)


# ---------------------------------------------------------------- plan parsing

PLAN = """# plan

## Decisions

### B01 · Something
- **file:** CLAUDE.md
- **verdict:** RULE
- **critical:** no
- **dest:** .claude/rules/a.md
- **paths:** src/**/*.ts
- **why:** scoped

### B02 · Critical thing
- **file:** CLAUDE.md
- **verdict:** KEEP
- **critical:** yes
- **why:** irreversible

## Notes

### Not a decision
"""

tmp = Path(__file__).parent / ".selftest-plan.md"
tmp.write_text(PLAN, encoding="utf-8")
try:
    parsed = A.parse_plan(tmp)
finally:
    tmp.unlink(missing_ok=True)

check("plan: decision count", sorted(parsed), ["B01", "B02"])
check("plan: field parsed", parsed["B01"]["paths"], "src/**/*.ts")
check("plan: stops at next heading", parsed["B02"].get("dest"), None)

# Regression: brace groups contain commas. Splitting naively turns one working
# pattern into two that match nothing, producing rules that never load. Found
# on a real repo where all four generated rules were silently dead.
check("globs: brace group is not split on its comma",
      A.split_globs("frontend/**/*.{ts,tsx}"), ["frontend/**/*.{ts,tsx}"])
check("globs: real separators still split",
      A.split_globs("src/**/*.ts, tests/**/*.ts"),
      ["src/**/*.ts", "tests/**/*.ts"])
check("globs: mixed braces and separators",
      A.split_globs("src/**/*.{ts,tsx}, lib/**/*.js, a/{b,c}/*.md"),
      ["src/**/*.{ts,tsx}", "lib/**/*.js", "a/{b,c}/*.md"])
check("globs: single pattern", A.split_globs("**/*.py"), ["**/*.py"])
check("globs: trailing separator ignored",
      A.split_globs("a/**, "), ["a/**"])
check("globs: nested braces survive",
      A.split_globs("s/{a,{b,c}}/*.ts"), ["s/{a,{b,c}}/*.ts"])

FAKE_BLOCKS = {"B01": {}, "B02": {}}
check("plan: valid plan has no errors", A.validate(dict(parsed), FAKE_BLOCKS), [])

bad = {"B01": {"id": "B01", "verdict": "RULE", "critical": "yes",
               "dest": "x.md", "paths": "**/*"}}
truthy("plan: critical block cannot be relocated",
       any("critical" in e for e in A.validate(bad, FAKE_BLOCKS)))

bad2 = {"B01": {"id": "B01", "verdict": "REFERENCE", "critical": "no",
                "dest": "r.md", "pointer": "read r.md for details"}}
truthy("plan: unbackticked pointer rejected",
       any("backticks" in e for e in A.validate(bad2, FAKE_BLOCKS)))

bad3 = {"B01": {"id": "B01", "verdict": "REFERENCE", "critical": "no",
                "dest": "r.md", "pointer": "read `r.md`", "hook": "@docs/x.md"}}
truthy("plan: bare @path in any field rejected",
       any("bare @path" in e for e in A.validate(bad3, FAKE_BLOCKS)))

bad4 = {"B01": {"id": "B01", "verdict": "SKILL", "critical": "no"}}
truthy("plan: SKILL requires name and description",
       len(A.validate(bad4, FAKE_BLOCKS)) >= 2)

truthy("plan: unknown id rejected",
       any("blocks.json" in e for e in A.validate(
           {"B99": {"id": "B99", "verdict": "KEEP", "critical": "no"}}, FAKE_BLOCKS)))


# ---------------------------------------------------------- freshness guard
# Regression test: an unguarded second apply cuts by stale offsets and can
# silently delete safety-critical content. It must be impossible.

import hashlib  # noqa: E402
import json  # noqa: E402
import tempfile  # noqa: E402

with tempfile.TemporaryDirectory() as td:
    tmp_root = Path(td)
    state = tmp_root / "state"
    state.mkdir()
    src = tmp_root / "CLAUDE.md"
    src.write_text("# A\n\nbody\n", encoding="utf-8")
    digest = hashlib.sha256(
        src.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
    fake_blocks = {"B01": {"file": str(src)}}
    decisions = {"B01": {"verdict": "DELETE"}}

    def write_inventory(sha) -> None:
        payload = {"files": [{"path": str(src), **({"sha256": sha} if sha else {})}]}
        (state / "inventory.json").write_text(json.dumps(payload), encoding="utf-8")

    write_inventory(digest)
    check("freshness: unchanged file passes",
          A.check_freshness(state, decisions, fake_blocks), [])

    src.write_text("# A\n\nbody edited\n", encoding="utf-8")
    truthy("freshness: modified file rejected",
           any("changed since discovery" in e
               for e in A.check_freshness(state, decisions, fake_blocks)))

    src.write_text("# A\n\nbody\n", encoding="utf-8")
    write_inventory(None)
    truthy("freshness: missing hash rejected, never skipped",
           any("no recorded hash" in e
               for e in A.check_freshness(state, decisions, fake_blocks)))

    write_inventory(digest)
    src.unlink()
    truthy("freshness: vanished file rejected",
           any("no longer exists" in e
               for e in A.check_freshness(state, decisions, fake_blocks)))

    src.write_text("# A\n\nbody\n", encoding="utf-8")
    check("freshness: KEEP verdicts need no freshness",
          A.check_freshness(state, {"B01": {"verdict": "KEEP"}}, fake_blocks), [])


# ------------------------------------------------------------- index handling

base = "# Doc\n\nbody text\n"
once = A.replace_index(base, A.render_index(["read `a.md`"]))
twice = A.replace_index(once, A.render_index(["read `b.md`"]))
truthy("index: inserted", "read `a.md`" in once)
truthy("index: replaced not duplicated", "read `a.md`" not in twice)
truthy("index: new pointer present", "read `b.md`" in twice)
check("index: exactly one marker pair", twice.count(A.INDEX_START), 1)
truthy("index: original body preserved", "body text" in twice)
check("index: empty pointers render nothing", A.render_index([]), "")

cleared = A.replace_index(once, "")
truthy("index: can be emptied", "read `a.md`" not in cleared)
truthy("index: body survives emptying", "body text" in cleared)


# --------------------------------------------------------------- block removal

TEXT = "# A\n\nkeep\n\n## B\n\ndrop\n\n## C\n\nkeep2\n"
segs = D.segment(TEXT)
target = next(s for s in segs if s["title"] == "B")
stripped = A.strip_blocks(TEXT, [(target["start"], target["end"])])
truthy("strip: removed block gone", "drop" not in stripped)
truthy("strip: neighbours intact", "keep" in stripped and "keep2" in stripped)
truthy("strip: no triple newlines", "\n\n\n" not in stripped)


# ------------------------------------------------------------ build() output
# build() is the function that actually generates the files users end up with:
# frontmatter, appends, block removal, and the managed index. Everything it
# produces is asserted here, per verdict.

SOURCE_DOC = """# Proj

## Universal

always run the linter

## Api

handlers validate input with zod

## Tests

tests use shared fixtures

## Runbook

1. bump version
2. publish

## Envtable

DATABASE_URL is required

## History

we picked X back in 2019

## Layout

- src/ has the source

## Backend

the worker pool is configured in config.yaml
"""

with tempfile.TemporaryDirectory() as td:
    broot = Path(td)
    bsrc = broot / "CLAUDE.md"
    bsrc.write_text(SOURCE_DOC, encoding="utf-8")

    segs = D.segment(SOURCE_DOC)
    by_title = {s["title"]: s for s in segs}
    check("build: fixture segmented as expected", len(segs), 9)

    order = ["Proj", "Universal", "Api", "Tests", "Runbook",
             "Envtable", "History", "Layout", "Backend"]
    bblocks = {f"B{i:02d}": {**by_title[t], "file": str(bsrc)}
               for i, t in enumerate(order, start=1)}

    bdecisions = {
        "B01": {"verdict": "KEEP", "critical": "no", "why": "title"},
        "B02": {"verdict": "KEEP", "critical": "no", "why": "universal"},
        "B03": {"verdict": "RULE", "critical": "no", "why": "api only",
                "dest": ".claude/rules/scoped.md", "paths": "src/api/**/*.ts"},
        # Same destination as B03 on purpose: destinations must merge, and
        # their path globs must union rather than overwrite.
        "B04": {"verdict": "RULE", "critical": "no", "why": "tests only",
                "dest": ".claude/rules/scoped.md", "paths": "tests/**/*.ts"},
        "B05": {"verdict": "SKILL", "critical": "no", "why": "procedure",
                "name": "cut-release",
                "description": "Cut and publish a release. Use when asked to "
                               "release, ship a version, or publish."},
        "B06": {"verdict": "REFERENCE", "critical": "no", "why": "bulky",
                "dest": ".claude/references/env.md",
                "pointer": "When editing env vars, read "
                           "`.claude/references/env.md`."},
        "B07": {"verdict": "ARCHIVE", "critical": "no", "why": "history",
                "dest": ".claude/references/_archive.md"},
        "B08": {"verdict": "DELETE", "critical": "no", "why": "derivable"},
        "B09": {"verdict": "NESTED", "critical": "no", "why": "backend subtree",
                "dest": "backend/CLAUDE.md"},
    }

    check("build: test plan is itself valid", A.validate(dict(bdecisions), bblocks), [])
    contents, bmanifest = A.build(broot, bdecisions, bblocks)

    def content_of(rel: str) -> str:
        p = broot / rel
        if p not in contents:
            FAILED.append(f"build: expected {rel} to be generated\n"
                          f"      generated: {[str(k) for k in contents]}")
            return ""
        return contents[p]

    # --- RULE: frontmatter, glob union, merged bodies
    rule = content_of(".claude/rules/scoped.md")
    truthy("build: rule starts with frontmatter", rule.startswith("---\npaths:"))
    truthy("build: rule keeps first glob", '"src/api/**/*.ts"' in rule)
    truthy("build: rule unions second glob", '"tests/**/*.ts"' in rule)
    truthy("build: rule has first body", "validate input with zod" in rule)
    truthy("build: rule has merged second body", "shared fixtures" in rule)
    check("build: trailer written once", rule.count("extracted by context-diet"), 1)

    # --- SKILL: correct location and triggering frontmatter
    skill = content_of(".claude/skills/cut-release/SKILL.md")
    truthy("build: skill has name", "name: cut-release" in skill)
    truthy("build: skill has description", "description: Cut and publish" in skill)
    truthy("build: skill body carried over", "bump version" in skill)

    # --- REFERENCE and ARCHIVE
    truthy("build: reference body",
           "DATABASE_URL" in content_of(".claude/references/env.md"))
    truthy("build: archive body",
           "back in 2019" in content_of(".claude/references/_archive.md"))

    # --- NESTED: lands in the subdirectory, gains no frontmatter, needs no pointer
    nested = content_of("backend/CLAUDE.md")
    truthy("build: nested body carried over", "worker pool" in nested)
    truthy("build: nested gets no frontmatter", not nested.startswith("---"))
    truthy("build: nested keeps its heading", "## Backend" in nested)

    # --- source rewrite
    rewritten = contents[bsrc]
    truthy("build: KEEP survives", "always run the linter" in rewritten)
    truthy("build: DELETE removed", "src/ has the source" not in rewritten)
    truthy("build: RULE removed from source", "validate input with zod" not in rewritten)
    truthy("build: SKILL removed from source", "bump version" not in rewritten)
    truthy("build: REFERENCE removed from source", "DATABASE_URL" not in rewritten)
    truthy("build: ARCHIVE removed from source", "back in 2019" not in rewritten)
    truthy("build: NESTED removed from source", "worker pool" not in rewritten)
    truthy("build: pointer inserted", "read `.claude/references/env.md`" in rewritten)
    check("build: exactly one index section", rewritten.count(A.INDEX_START), 1)
    truthy("build: no triple newlines left", "\n\n\n" not in rewritten)

    # --- INDEX.md catalogues references and archive only
    index = content_of(".claude/references/INDEX.md")
    truthy("build: index lists reference", "env.md" in index)
    truthy("build: index lists archive", "_archive.md" in index)
    truthy("build: index omits rules", "scoped.md" not in index)
    truthy("build: index omits skills", "cut-release" not in index)
    truthy("build: index omits nested", "backend/CLAUDE.md" not in index)

    # --- manifest
    check("build: manifest covers every decision", len(bmanifest["entries"]), 9)
    verdict_counts: dict[str, int] = {}
    for ent in bmanifest["entries"]:
        verdict_counts[ent["verdict"]] = verdict_counts.get(ent["verdict"], 0) + 1
    check("build: manifest verdict counts", verdict_counts,
          {"KEEP": 2, "RULE": 2, "SKILL": 1, "REFERENCE": 1,
           "ARCHIVE": 1, "DELETE": 1, "NESTED": 1})

    # --- destination/source collision must be refused, not silently mangled
    check("build: clean plan has no destination collisions",
          A.check_destinations(broot, bdecisions, bblocks), [])
    collide = {"B03": {"verdict": "REFERENCE", "critical": "no",
                       "dest": "CLAUDE.md", "pointer": "read `CLAUDE.md`"}}
    truthy("build: destination this plan strips is rejected",
           any("removes blocks from" in e
               for e in A.check_destinations(broot, collide, bblocks)))
    # ...but a file that merely HAS blocks, while this plan strips nothing from
    # it, is a legitimate target. This is the @import case: an imported doc is
    # a source (it is eager, so it gets segmented) yet pointing at it is
    # exactly right. An over-broad guard here rejects the highest-value fix
    # the tool can make.
    other = broot / "other.md"
    other.write_text("# Other\n\npre-existing\n", encoding="utf-8")
    two_files = {**bblocks, "B90": {**by_title["Proj"], "file": str(other)}}
    untouched = {"B02": {"verdict": "POINTER", "critical": "no",
                         "dest": "other.md", "pointer": "read `other.md`"}}
    check("build: source untouched by the plan is a legal POINTER target",
          A.check_destinations(broot, untouched, two_files), [])
    collide_skill = {"B03": {"verdict": "SKILL", "critical": "no",
                             "name": "x", "description": "y"}}
    check("build: skill destination never collides",
          A.check_destinations(broot, collide_skill, bblocks), [])
    truthy("build: DELETE records what it removed",
           any(e["verdict"] == "DELETE" and e.get("deleted_text")
               for e in bmanifest["entries"]))
    truthy("build: relocations record a destination",
           all(e.get("dest") for e in bmanifest["entries"]
               if e["verdict"] in A.RELOCATING))

    # --- POINTER: removes the block, emits a pointer, writes no content
    existing_doc = broot / "docs" / "already-here.md"
    existing_doc.parent.mkdir(parents=True, exist_ok=True)
    existing_doc.write_text("# Already here\n\npre-existing content\n",
                            encoding="utf-8")
    pdec = {"B02": {"verdict": "POINTER", "critical": "no",
                    "dest": "docs/already-here.md",
                    "pointer": "When touching the parser, read "
                               "`docs/already-here.md`.",
                    "why": "undo an @import"}}
    check("build: POINTER plan validates",
          A.validate(dict(pdec), bblocks) +
          A.check_destinations(broot, pdec, bblocks), [])
    pcontents, pmanifest = A.build(broot, pdec, bblocks)
    truthy("build: POINTER writes nothing to its destination",
           existing_doc not in pcontents)
    check("build: POINTER destination content untouched",
          existing_doc.read_text(encoding="utf-8"),
          "# Already here\n\npre-existing content\n")
    psrc = pcontents[bsrc]
    truthy("build: POINTER removes the block from source",
           "always run the linter" not in psrc)
    truthy("build: POINTER leaves a pointer", "already-here.md" in psrc)
    check("build: POINTER records that it wrote no content",
          pmanifest["entries"][0]["wrote_content"], False)

    missing_target = {"B02": {"verdict": "POINTER", "critical": "no",
                              "dest": "docs/never-created.md",
                              "pointer": "read `docs/never-created.md`"}}
    truthy("build: POINTER at a nonexistent target is rejected",
           any("does not exist" in e
               for e in A.check_destinations(broot, missing_target, bblocks)))

    # --- the premise: nothing generated may load eagerly by accident
    for path, text in contents.items():
        if A.BARE_IMPORT_RE.search(D.mask_code(text)):
            FAILED.append(f"build: generated {path.name} contains a bare @path")

    # --- KEEP-only plans must not fabricate files
    only_keep, _ = A.build(broot, {"B01": {"verdict": "KEEP", "critical": "no"}},
                           bblocks)
    check("build: KEEP-only plan writes nothing", list(only_keep), [])


# ------------------------------------------------------------ commit / rollback
# The transaction is the last line of defence: a half-applied plan leaves a
# CLAUDE.md with content removed and nowhere to find it.

with tempfile.TemporaryDirectory() as td:
    croot = Path(td)
    existing = croot / "existing.md"
    existing.write_text("ORIGINAL\n", encoding="utf-8")
    fresh = croot / "sub" / "fresh.md"
    backups = croot / "backups"

    ok = A.commit({existing: "REWRITTEN\n", fresh: "NEW\n"}, backups)
    check("commit: existing file rewritten",
          existing.read_text(encoding="utf-8"), "REWRITTEN\n")
    check("commit: new file created in a new directory",
          fresh.read_text(encoding="utf-8"), "NEW\n")
    check("commit: only pre-existing files are backed up", len(ok), 1)
    truthy("commit: backup holds the original content",
           any(b.read_text(encoding="utf-8") == "ORIGINAL\n" for _, b in ok))
    check("commit: no temp files left behind",
          list(croot.rglob("*.context-diet-tmp")), [])

with tempfile.TemporaryDirectory() as td:
    croot = Path(td)
    good = croot / "good.md"
    good.write_text("ORIGINAL\n", encoding="utf-8")
    made = croot / "made.md"
    # A file, not a directory: mkdir of its "parent" raises mid-transaction.
    blocker = croot / "blocker.md"
    blocker.write_text("i am a file\n", encoding="utf-8")
    doomed = blocker / "nested" / "bad.md"

    raised = False
    try:
        A.commit({good: "REWRITTEN\n", made: "NEW\n", doomed: "X\n"},
                 croot / "backups")
    except Exception:
        raised = True

    truthy("rollback: failure propagates to the caller", raised)
    check("rollback: modified file restored",
          good.read_text(encoding="utf-8"), "ORIGINAL\n")
    truthy("rollback: created file removed", not made.exists())
    truthy("rollback: unrelated file untouched", blocker.is_file())
    check("rollback: no temp files left behind",
          list(croot.rglob("*.context-diet-tmp")), [])


# --------------------------------------------------------- verify.py checks
# Each check is tested for BOTH outcomes. A check that cannot fail is worse
# than no check, because it reports "ok".

import reaudit as R  # noqa: E402


def fresh_root(td: str, home_too: bool = True) -> tuple[Path, Path]:
    root = Path(td) / "proj"
    home = Path(td) / "home"
    (root / ".claude").mkdir(parents=True)
    if home_too:
        (home / ".claude").mkdir(parents=True)
    return root, home


# --- check_skills
with tempfile.TemporaryDirectory() as td:
    vroot, vhome = fresh_root(td)
    skills = vroot / ".claude" / "skills"
    (skills / "good").mkdir(parents=True)
    (skills / "good" / "SKILL.md").write_text(
        "---\nname: good\ndescription: A sufficiently long description that "
        "explains when to trigger this skill.\n---\n\nbody here\n",
        encoding="utf-8")
    res = V.Result()
    V.check_skills(vroot, res)
    check("verify: valid skill passes", res.failures, [])

    (skills / "nodesc").mkdir(parents=True)
    (skills / "nodesc" / "SKILL.md").write_text(
        "---\nname: nodesc\n---\n\nbody\n", encoding="utf-8")
    (skills / "nobody").mkdir(parents=True)
    (skills / "nobody" / "SKILL.md").write_text(
        "---\nname: nobody\ndescription: long enough description for the "
        "trigger to work correctly\n---\n", encoding="utf-8")
    res = V.Result()
    V.check_skills(vroot, res)
    truthy("verify: missing description caught",
           any("description" in f for f in res.failures))
    truthy("verify: empty skill body caught",
           any("empty" in f for f in res.failures))

# --- check_globs
with tempfile.TemporaryDirectory() as td:
    vroot, vhome = fresh_root(td)
    (vroot / "src").mkdir()
    (vroot / "src" / "a.ts").write_text("x", encoding="utf-8")
    rules = vroot / ".claude" / "rules"
    rules.mkdir()
    (rules / "live.md").write_text(
        '---\npaths:\n  - "src/**/*.ts"\n---\n\nrule\n', encoding="utf-8")
    res = V.Result()
    V.check_globs(vroot, res, home=vhome)
    check("verify: reachable glob passes", res.failures, [])

    (rules / "dead.md").write_text(
        '---\npaths:\n  - "nowhere/**/*.rs"\n---\n\nrule\n', encoding="utf-8")
    res = V.Result()
    V.check_globs(vroot, res, home=vhome)
    truthy("verify: unreachable glob caught",
           any("never load" in f for f in res.failures))

# --- check_pointers
with tempfile.TemporaryDirectory() as td:
    vroot, vhome = fresh_root(td)
    (vroot / ".claude" / "references").mkdir()
    (vroot / ".claude" / "references" / "real.md").write_text("x", encoding="utf-8")
    (vroot / "CLAUDE.md").write_text(
        f"# P\n\n{A.INDEX_START}\n\n## Further reading\n\n"
        "- When editing config, read `.claude/references/real.md`.\n\n"
        f"{A.INDEX_END}\n", encoding="utf-8")
    res = V.Result()
    V.check_pointers(vroot, res, home=vhome)
    check("verify: resolvable pointer passes", res.failures, [])

    (vroot / "CLAUDE.md").write_text(
        f"# P\n\n{A.INDEX_START}\n\n"
        "- When editing config, read `.claude/references/ghost.md`.\n\n"
        f"{A.INDEX_END}\n", encoding="utf-8")
    res = V.Result()
    V.check_pointers(vroot, res, home=vhome)
    truthy("verify: dangling pointer caught",
           any("does not exist" in f for f in res.failures))

# --- check_no_imports
with tempfile.TemporaryDirectory() as td:
    vroot, vhome = fresh_root(td)
    (vroot / "CLAUDE.md").write_text(
        "# P\n\nsee `@README` which is inert\n", encoding="utf-8")
    res = V.Result()
    V.check_no_imports(vroot, res, home=vhome)
    check("verify: backticked path is not an import", res.failures, [])

    # An import only costs context if it resolves to a real file.
    (vroot / "docs").mkdir(exist_ok=True)
    (vroot / "docs" / "thing.md").write_text("content", encoding="utf-8")
    (vroot / "CLAUDE.md").write_text("# P\n\n@docs/thing.md\n", encoding="utf-8")
    res = V.Result()
    V.check_no_imports(vroot, res, home=vhome)
    truthy("verify: resolving import caught",
           any("load at" in f for f in res.failures))

    # Regression: JSDoc tags are not imports. A CLAUDE.md documenting JSDoc
    # is full of @fileoverview/@param/@returns; flagging them made a real
    # apply fail verification for no reason.
    (vroot / "CLAUDE.md").write_text(
        "# P\n\nMUST use @fileoverview and @param in every module.\n",
        encoding="utf-8")
    res = V.Result()
    V.check_no_imports(vroot, res, home=vhome)
    check("verify: JSDoc tags are not imports", res.failures, [])
    check("verify: JSDoc tags do not even warn", res.warnings, [])

    # Path-shaped but dangling: warn, do not fail.
    (vroot / "CLAUDE.md").write_text("# P\n\n@docs/missing.md\n", encoding="utf-8")
    res = V.Result()
    V.check_no_imports(vroot, res, home=vhome)
    check("verify: dangling import is not a failure", res.failures, [])
    truthy("verify: dangling import warns",
           any("resolves to nothing" in w for w in res.warnings))

# --- check_accounting
with tempfile.TemporaryDirectory() as td:
    vroot, _ = fresh_root(td)
    src = vroot / "CLAUDE.md"
    src.write_text("# P\n\nkept content\n", encoding="utf-8")
    dest = vroot / ".claude" / "references" / "moved.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("## Moved\n\nmoved content\n", encoding="utf-8")

    clean = {"entries": [
        {"id": "B01", "title": "Moved", "source": str(src),
         "verdict": "REFERENCE", "dest": str(dest)},
        {"id": "B02", "title": "Gone", "source": str(src),
         "verdict": "DELETE", "deleted_text": "obliterated text"},
    ]}
    res = V.Result()
    V.check_accounting(vroot, clean, res)
    check("verify: clean accounting passes", res.failures, [])

    missing_dest = {"entries": [
        {"id": "B01", "title": "Moved", "source": str(src),
         "verdict": "REFERENCE", "dest": str(vroot / "nope.md")}]}
    res = V.Result()
    V.check_accounting(vroot, missing_dest, res)
    truthy("verify: missing destination caught",
           any("does not exist" in f for f in res.failures))

    not_deleted = {"entries": [
        {"id": "B02", "title": "Kept", "source": str(src),
         "verdict": "DELETE", "deleted_text": "kept content"}]}
    res = V.Result()
    V.check_accounting(vroot, not_deleted, res)
    truthy("verify: undeleted DELETE caught",
           any("still present" in f for f in res.failures))


# ------------------------------------------------------------ reaudit helpers

check("reaudit: pointer with trigger accepted",
      bool(R.TRIGGER_RE.match("When editing env vars, read `x.md`.")), True)
check("reaudit: pointer without trigger rejected",
      bool(R.TRIGGER_RE.match("See `x.md` for details.")), False)
truthy("reaudit: broad trigger detected",
       R.TOO_BROAD_RE.search("When working, always read `x.md`."))
truthy("reaudit: narrow trigger not flagged as broad",
       not R.TOO_BROAD_RE.search("Before deploying, read `x.md`."))
check("reaudit: pointer lines extracted",
      R.pointer_lines("- When x, read `a.md`.\nprose\n- After y, read `b.md`."),
      ["- When x, read `a.md`.", "- After y, read `b.md`."])
check("reaudit: lines without a path are not pointers",
      R.pointer_lines("- just a bullet\n"), [])


# ------------------------------------------------------- discovery fixtures
# Every instruction-file type Claude Code can load, in one synthetic tree.
# None of these exist on the development machine, so without this fixture they
# are handled in theory only. The classification asserted here IS the product:
# get eager/lazy wrong and every token figure downstream is wrong.

with tempfile.TemporaryDirectory() as td:
    droot = Path(td) / "proj"
    dhome = Path(td) / "home"
    (droot / ".claude" / "rules").mkdir(parents=True)
    (dhome / ".claude" / "rules").mkdir(parents=True)
    (droot / "docs").mkdir()
    (droot / "backend").mkdir()
    (droot / "node_modules" / "pkg").mkdir(parents=True)

    managed = Path(td) / "policy" / "CLAUDE.md"
    managed.parent.mkdir(parents=True)
    managed.write_text("# Org policy\n\ncompany wide rule\n", encoding="utf-8")

    # eager: loaded in full at launch
    (droot / "CLAUDE.md").write_text(
        "# Root\n\nroot rule\n\nsee @docs/imported.md for more\n", encoding="utf-8")
    (droot / "CLAUDE.local.md").write_text(
        "# Local\n\npersonal preference\n", encoding="utf-8")
    (droot / ".claude" / "CLAUDE.md").write_text(
        "# Claude dir\n\nanother root rule\n", encoding="utf-8")
    (dhome / ".claude" / "CLAUDE.md").write_text(
        "# User\n\nglobal preference\n", encoding="utf-8")
    (droot / ".claude" / "rules" / "unscoped.md").write_text(
        "# Unscoped\n\napplies always\n", encoding="utf-8")
    (dhome / ".claude" / "rules" / "userwide.md").write_text(
        "# Userwide\n\nno paths key\n", encoding="utf-8")
    # a two-hop import chain
    (droot / "docs" / "imported.md").write_text(
        "# Imported\n\nfirst hop\n\nand @deeper.md too\n", encoding="utf-8")
    (droot / "docs" / "deeper.md").write_text(
        "# Deeper\n\nsecond hop\n", encoding="utf-8")

    # lazy: loaded only on demand
    (droot / ".claude" / "rules" / "scoped.md").write_text(
        '---\npaths:\n  - "backend/**/*.py"\n---\n\nscoped rule\n', encoding="utf-8")
    (dhome / ".claude" / "rules" / "userscoped.md").write_text(
        '---\npaths:\n  - "**/*.ts"\n---\n\nuser scoped\n', encoding="utf-8")
    (droot / "backend" / "CLAUDE.md").write_text(
        "# Backend\n\nsubtree rule\n", encoding="utf-8")

    # must be ignored entirely
    (droot / "node_modules" / "pkg" / "CLAUDE.md").write_text(
        "# Vendor\n\nnot ours\n", encoding="utf-8")

    inv, dblocks = D.discover(droot, home=dhome, managed=managed)
    found = {}
    for f in inv["files"]:
        p = Path(f["path"])
        # Keys must be unique per fixture file. Anything outside the fixture
        # (the upward walk legitimately finds real ancestor CLAUDE.md files on
        # the host) keeps its full path so it cannot collide with a fixture key.
        if droot in p.parents or p.parent == droot:
            key = p.relative_to(droot).as_posix()
        elif dhome in p.parents:
            key = "HOME/" + p.relative_to(dhome).as_posix()
        elif p == managed:
            key = "MANAGED"
        else:
            key = str(p)
        found[key] = f

    for rel, kind in [
        ("CLAUDE.md", "project-claude-md"),
        ("CLAUDE.local.md", "local-claude-md"),
        (".claude/CLAUDE.md", "project-claude-md"),
        ("HOME/.claude/CLAUDE.md", "user-claude-md"),
        (".claude/rules/unscoped.md", "project-rule"),
        ("HOME/.claude/rules/userwide.md", "user-rule"),
        ("docs/imported.md", "import"),
        ("docs/deeper.md", "import"),
        ("MANAGED", "managed-policy"),
    ]:
        if rel not in found:
            FAILED.append(f"discover: expected to find {rel}\n"
                          f"      found: {sorted(found)}")
            continue
        check(f"discover: {rel} is eager", found[rel]["eager"], True)
        check(f"discover: {rel} kind", found[rel]["kind"], kind)

    for rel in (".claude/rules/scoped.md", "HOME/.claude/rules/userscoped.md",
                "backend/CLAUDE.md"):
        if rel not in found:
            FAILED.append(f"discover: expected to find {rel}")
            continue
        check(f"discover: {rel} is lazy", found[rel]["eager"], False)

    check("discover: scoped rule records its globs",
          found[".claude/rules/scoped.md"]["paths"], ["backend/**/*.py"])
    check("discover: nested CLAUDE.md classified as nested",
          found["backend/CLAUDE.md"]["kind"], "nested-claude-md")
    truthy("discover: node_modules ignored",
           not any("node_modules" in k for k in found))
    check("discover: import chain followed two hops",
          found["docs/deeper.md"]["depth"], 2)
    truthy("discover: import records its importer",
           found["docs/imported.md"]["imported_by"].endswith("CLAUDE.md"))
    truthy("discover: every eager file has a hash for the freshness guard",
           all(f.get("sha256") for f in inv["files"] if f["eager"]))

    truthy("discover: eager total counts more than the root file",
           inv["totals"]["eager_tokens"] > found["CLAUDE.md"]["tokens"])
    check("discover: lazy files counted", inv["totals"]["lazy_files"], 3)

    # Managed policy is deliberately excluded from segmentation: it is
    # org-deployed and cannot be edited or excluded by this tool.
    truthy("discover: managed policy produces no editable blocks",
           not any(b["file"] == str(managed) for b in dblocks.values()))
    truthy("discover: lazy files produce no blocks",
           not any("backend" in Path(b["file"]).parts for b in dblocks.values()))


# ---------------------------------------------------------------------- report

if FAILED:
    print(f"{len(FAILED)} FAILED\n")
    for f in FAILED:
        print(f"  - {f}")
    raise SystemExit(1)
print("all self-tests passed")
