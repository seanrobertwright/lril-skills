# Loading mechanisms, routing, and the criticality gate

Everything here is verified against the official Claude Code memory
documentation (`code.claude.com/docs/en/memory`). Where the docs state
something verbatim that people commonly get wrong, the quote is included.

## What actually costs every-session context

| Mechanism | Location | Loads | Costs eager tokens? |
|---|---|---|---|
| Managed policy CLAUDE.md | OS-specific policy path | At launch, cannot be excluded | **Yes** |
| User CLAUDE.md | `~/.claude/CLAUDE.md` | At launch | **Yes** |
| Project CLAUDE.md | `./CLAUDE.md` or `./.claude/CLAUDE.md` | At launch | **Yes** |
| Local CLAUDE.md | `./CLAUDE.local.md` | At launch | **Yes** |
| Ancestor CLAUDE.md | Any parent directory | At launch | **Yes** |
| `@path` imports | Anywhere in a loaded CLAUDE.md | Expanded at launch, depth ≤ 4 | **Yes** |
| Unscoped rules | `.claude/rules/*.md` with no `paths:` | At launch | **Yes** |
| User rules | `~/.claude/rules/*.md` with no `paths:` | At launch | **Yes** |
| Auto-memory index | `MEMORY.md` | At launch, first 200 lines / 25 KB | **Yes** (capped) |
| **Path-scoped rules** | `.claude/rules/*.md` with `paths:` | When Claude reads a matching file | **No** |
| **Nested CLAUDE.md** | Subdirectory below cwd | When Claude reads files in that dir | **No** |
| **Skills** | `.claude/skills/*/SKILL.md` | On description match or invocation | **No** |
| **Referenced docs** | Any path named in prose | When Claude chooses to read it | **No** |
| **Memory topic files** | `memory/*.md` besides the index | On demand | **No** |

Only the four bold rows are real progressive disclosure. Everything above them
is paid for on every single session, whatever file it lives in.

### The `@import` trap

> "Splitting into `@path` imports helps organization but doesn't reduce
> context, since imported files load at launch."

> "Imported files are expanded and loaded into context at launch alongside the
> CLAUDE.md that references them."

An `@import` is a *file organization* tool. It is never a pruning tool. Never
emit one. When auditing a file that already uses them, treat the imported
content as if it were pasted inline — because it is — and judge it on the same
terms as the rest.

**Undoing an import is usually the single highest-value change available**, and
it moves no content: the target file already exists and stays exactly where it
is. Only the loading mechanism is wrong. Use the `POINTER` verdict, which
removes the block, writes a trigger-stating pointer, and writes nothing to the
destination. A real repo audited with this skill had five imports costing 8,130
eager tokens — 73% of its entire startup context — behind four short lines.

`POINTER` requires the destination to already exist. If it does not, the
content has to be moved, which is `REFERENCE`, not `POINTER`.

To mention a path without importing it, wrap it in backticks. Import parsing
skips code spans and fenced code blocks. This matters: a pointer line **must**
put the path in backticks, or it silently becomes an import and defeats the
whole extraction.

### Free structure

> "Block-level HTML comments (`<!-- maintainer notes -->`) in CLAUDE.md files
> are stripped before the content is injected into Claude's context."

Use this for provenance and for machine-readable markers. Both cost zero
tokens:

```markdown
<!-- context-diet:index:start -->
## Further reading
- Before deploying, read `.claude/references/deploy.md`.
<!-- context-diet:index:end -->
```

## The `/compact` caveat

> "Project-root CLAUDE.md survives compaction: after `/compact`, Claude
> re-reads it from disk and re-injects it into the session. Nested CLAUDE.md
> files in subdirectories and rules with `paths:` frontmatter are not
> re-injected automatically; they reload the next time Claude reads a file in
> that subdirectory or a file matching the rule's patterns."

Consequence: content moved to a path-scoped rule or a nested CLAUDE.md can be
**absent from context for an arbitrary stretch of a long session**. For a
style preference that is a shrug. For "never force-push to main" it is a real
incident.

## Criticality gate

Run this **before** any routing decision. It overrides every other rule.

A block is **safety-critical** if violating it causes harm that is
irreversible, externally visible, or expensive:

- Destructive operations — `force-push`, `reset --hard`, `rm -rf`, `DROP`,
  history rewriting, branch or tag deletion
- Production and live systems — prod databases, live config, running services
- Secrets and credentials — what must never be logged, committed, or echoed
- Money — billing, payments, provisioning paid resources
- Anything outward-facing — publishing, sending, posting, deploying, notifying
- Legal, licensing, privacy, and compliance constraints
- Any rule whose wording is "never" or "under no circumstances"

**Safety-critical blocks stay in root CLAUDE.md.** Do not move them into a
path-scoped rule, a nested CLAUDE.md, a skill, or a reference — not even when
they are narrowly scoped and would otherwise be obvious extraction candidates.

Two things worth saying in the plan when you find one:

1. Keeping it costs eager tokens on purpose. Name the tradeoff rather than
   hiding it.
2. CLAUDE.md is not enforcement. The docs are explicit: instructions "shape
   Claude's behavior but are not a hard enforcement layer." A truly critical
   constraint should *also* become a `PreToolUse` hook or a
   `permissions.deny` entry, which apply regardless of what Claude decides.
   Flag hook candidates in the plan. Do not write hooks as part of this
   skill — recommend them.

## Routing decision tree

Evaluate in order. First match wins.

1. **Safety-critical?** → `KEEP`. Flag hook candidacy. Stop.
2. **Is it an `@import`, or a stub whose only content points at an existing
   file?** → `POINTER`. Cheapest and usually largest win; nothing moves.
3. **Claims fail verification** — command, path, or dependency no longer
   exists? → `DELETE` (stale). Quote the failed check.
3. **Derivable by reading the repo** — directory listings, dependency
   inventories, file-by-file architecture tours, generated API surface? →
   `DELETE`. Claude can read the codebase; restating it is pure cost.
   Keep the *non-obvious* part if there is one: rationale, a pitfall, or a
   convention that differs from the tool's default.
4. **Already covered elsewhere** — an installed skill, an existing rule, or
   auto-memory says the same thing? → `DELETE`, naming the duplicate. If the
   two disagree, that is a conflict: `ASK`. Contradictory instructions are
   worse than either instruction alone.
5. **A multi-step procedure** — a runbook, a sequence, a "how to do X"? →
   `SKILL`. The docs are direct: "If an entry is a multi-step procedure or only
   matters for one part of the codebase, move it to a skill or a path-scoped
   rule instead." Needs a `description` written for triggering, not for
   summarizing.
6. **Scoped to files matching a glob** — one language, extension, or
   directory? → `RULE` with `paths:`. No pointer needed; it self-triggers.
   Verify the glob matches real files. Prefer the narrowest correct glob.
7. **Scoped to one subtree, but too broad or too varied for a glob** →
   `NESTED` CLAUDE.md in that directory.
8. **Bulky, unscoped, occasionally needed** — env var tables, schema dumps,
   API references, ADR rationale, long examples? → `REFERENCE` in
   `.claude/references/` plus a trigger-stating pointer line.
9. **Bulky, unscoped, and probably never needed** — historical notes,
   superseded decisions, onboarding narrative? → `ARCHIVE` to
   `.claude/references/_archive.md`, unreferenced. Costs nothing, still
   recoverable without git.
10. **Otherwise** → `KEEP`. Universally applicable, short, and load-bearing.

When two branches both fit, prefer the one that needs no pointer — a
path-scoped rule beats a reference, because it does not depend on Claude
choosing to read anything.

## Glob guidance for `paths:`

- Narrowest correct pattern. `src/api/**/*.ts` beats `**/*.ts`.
- Multiple patterns are fine; brace expansion works (`src/**/*.{ts,tsx}`) but
  shares a 1,000-pattern expansion budget across the rule.
- A `[` that cannot be read as a bracket expression makes the pattern match
  nothing. Escape literal brackets as `\[`.
- Always verify against the real tree. A glob matching zero files is a rule
  that never loads — silent, total failure.
