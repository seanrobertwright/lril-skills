# Content taxonomy and evidence checks

Four categories are **default-extract**: guilty until proven universal. The
rest default to `KEEP`. Every verdict must cite evidence, not vibes.

## Default-extract categories

### 1. Procedures and runbooks

Release processes, migrations, deploy steps, environment setup, onboarding
walkthroughs, "how to add a new X" guides, debugging playbooks.

Tell: numbered steps, or any sequence where order matters.

Default verdict: `SKILL`. A procedure needs to be *invoked*, and a skill is the
only mechanism that carries its own trigger description.

Exception: a one-line command everyone needs constantly (`npm test` before
committing) is not a procedure. It stays.

### 2. Path- and stack-scoped rules

Anything true only for one language, framework, directory, or file type.
"React components use function syntax." "Python code must have type hints."
"Handlers in `src/api/` validate input."

Tell: the rule names a technology, an extension, or a directory.

Default verdict: `RULE` with the narrowest `paths:` glob that covers it.
`NESTED` when the scope is a subtree but too varied to glob cleanly.

Watch for the disguised case: a rule phrased universally that is *actually*
scoped. "Always use `pytest` fixtures" only matters in test files.

### 3. Codebase-derivable facts

Directory trees, dependency lists, file inventories, module-by-module
architecture tours, generated API surface, "the project uses TypeScript and
React."

Tell: Claude could learn it in one `ls`, one `Read`, or one `Glob`.

Default verdict: `DELETE`. This is the highest-yield category and the one users
resist most, because these sections look like the most "useful" documentation.
They are not — they are a stale copy of something authoritative.

Salvage rule: keep the part that is *not* derivable. "`src/legacy/` is
unmaintained, do not extend it" survives; the directory listing around it does
not. Split the block if needed.

### 4. Reference data and rationale

Env var tables, config schemas, error code lists, API endpoint catalogues, long
code examples, ADR-style "why we chose X over Y" history.

Tell: bulky, factual, consulted rather than followed.

Default verdict: `REFERENCE` with a pointer, or `ARCHIVE` when it documents a
decision nobody needs to act on.

Rationale is the subtle one. "We use Postgres, not Mongo, because of X" does
not change behavior on most sessions — extract it. But "never add a Mongo
dependency" *is* a behavioral rule — keep the rule, extract the essay.

## What survives by default

- Conventions that differ from the tool's or ecosystem's default. These are
  exactly what Claude gets wrong without being told.
- Short, universal, verifiable commands: build, test, lint, typecheck.
- Pitfalls and gotchas — non-obvious traps with real consequences.
- Anything safety-critical (see the criticality gate).
- Repo-wide style rules that genuinely apply to every file.

## Evidence checks

Run the check before assigning the verdict. Quote the result in the plan.

| Claim in the block | Check | Fails ⇒ |
|---|---|---|
| "Run `npm run foo`" | `scripts.foo` in `package.json` | stale → `DELETE` |
| "Run `make bar`" | `bar:` target in `Makefile` | stale → `DELETE` |
| "Run `uv run pytest`" | dep in `pyproject.toml`; binary resolves | stale → `DELETE` |
| "Code lives in `src/x/`" | directory exists | stale → `DELETE` |
| "We use `<library>`" | in manifest **and** imported somewhere | stale → `DELETE` |
| "Components use X" | count files matching the implied glob | narrow ⇒ `RULE` |
| "Always do X" | count files where X could apply | narrow ⇒ `RULE` |
| Architecture description | can it be reconstructed by reading? | yes ⇒ `DELETE` |
| Any procedure | does an installed skill already cover it? | yes ⇒ `DELETE` |
| Any rule | does an existing rule or `MEMORY.md` say it? | yes ⇒ `DELETE` |

### Frequency drives scoping

For every candidate rule, count the files it could apply to and compare to the
repo total. This is the single most useful number in the audit.

```
matching / total    verdict
< ~15%              RULE with paths:  (clear win)
~15–60%             judgement — prefer RULE if the glob is clean and precise
> ~60%              KEEP — scoping it costs more in complexity than it saves
```

Counts, not impressions. `Glob` the pattern and count; compare against the
total tracked-file count.

### Conflicts

If two loaded files give different guidance on the same behavior, that is not a
pruning decision — it is a bug. The docs warn that Claude "may pick one
arbitrarily." Always `ASK`, never resolve it silently, and surface it near the
top of the chat digest. Resolving a contradiction is often worth more than any
token saved.

## Global vs project files

`~/.claude/CLAUDE.md` costs eager tokens in **every project on the machine**,
so a line there is far more expensive than the same line in one project. Judge
it harder:

- Project-specific content in the global file → move it to that project.
- Stack-specific content ("in Python, do X") → `~/.claude/rules/` with `paths:`.
- Personal workflow procedures → a personal skill in `~/.claude/skills/`.
- Only genuinely cross-project, cross-language preferences stay.

Symmetrically: content in a project CLAUDE.md that reflects one person's
preference belongs in `CLAUDE.local.md` (gitignored), not the shared file.

## Team-shared files

A project `CLAUDE.md` is committed and read by teammates. Before restructuring
one, say so and note that extracted files must be committed together — a
pointer to an uncommitted `.claude/references/` file is a broken pointer for
everyone else. Check whether `.claude/` is gitignored before routing anything
there.
