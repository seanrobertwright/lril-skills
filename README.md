<p align="center">
  <img src="assets/logo.svg" alt="LRIL Skills" width="820">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-1.0.0-blue?style=flat-square" alt="Version">
  <img src="https://img.shields.io/badge/skills-34-blueviolet?style=flat-square" alt="Skills">
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="License">
  <img src="https://img.shields.io/badge/node-%3E%3D18-brightgreen?style=flat-square" alt="Node">
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey?style=flat-square" alt="Platform">
</p>

<p align="center">
  <strong>Production-grade skills for Claude Code that handle the work you shouldn't have to think about.</strong>
  <br>
  Browser automation, end-to-end testing, acceptance testing, visual diagramming, intent planning, and
  Docker port management — plus 25 mirrored engineering skills. Installed in seconds.
</p>

---

## Quick Start

```bash
npx github:seanrobertwright/lril-skills
```

That's it. An interactive installer walks you through selecting skills and choosing where to install them (globally or per-project). Restart Claude Code and your new skills are ready.

<p align="center">
  <img width="550" alt="installer" src="https://github.com/user-attachments/assets/placeholder-installer-screenshot.png">
</p>

## Skills at a glance

**34 skills** — 9 authored here, 25 mirrored from other authors.

| | |
|---|---|
| **Testing & QA** | [`agent-browser`](#agent-browser--browser-automation) · [`e2e-test`](#e2e-test--end-to-end-testing) · [`creating-uat`](#creating-uat--user-acceptance-testing) · [`processing-uat`](#processing-uat--turn-uat-results-into-a-fix-plan) · `tdd` · `diagnosing-bugs` |
| **Planning & design** | [`intent-engine`](#intent-engine--structured-intent-planning) · `codebase-design` · `domain-modeling` · `grilling` · `prototype` · `to-prd` · `to-issues` |
| **Workflow** | [`lril`](#lril--second-brain-workflow-commands) · `implement` · `triage` · `handoff` · `resolving-merge-conflicts` |
| **Environment** | [`port-authhority`](#port-authhority--docker-port-conflict-manager) · [`context-diet`](#context-diet--shrink-what-loads-every-session) · `setup-pre-commit` · `git-guardrails-claude-code` |
| **Communication** | [`excalidraw-diagram`](#excalidraw-diagram--visual-diagramming) · `edit-article` · `teach` · `obsidian-vault` |

---

## Authored here

### `agent-browser` — Browser Automation

Gives Claude hands-on control of a real browser. Navigate pages, click elements, fill forms, take screenshots, and extract data — all through a clean CLI that Claude can drive autonomously.

```
agent-browser open https://example.com
agent-browser snapshot -i          # returns interactive element refs
agent-browser click @e3            # click by ref
agent-browser fill @e5 "hello"     # type into inputs
agent-browser screenshot page.png  # capture the page
```

**Use it when:** you need Claude to test a web app, scrape structured data, fill out forms, or verify UI behavior against a live page.

---

### `e2e-test` — End-to-End Testing

Launches parallel sub-agents that research your codebase (structure, database schema, potential bugs), then systematically tests every user journey using a real browser — taking screenshots, validating UI/UX, and querying the database to confirm records were created correctly.

**Use it when:** you've finished implementing a feature and want to validate everything works before code review. One command replaces a manual QA pass.

---

### `creating-uat` — User Acceptance Testing

Builds a complete UAT for a codebase and hands it to a **human** tester. Reads the repo, maps every user-facing surface, and produces three things:

1. **A markdown checklist** covering setup, every UI surface and state, every endpoint / CLI command / background job, the unhappy paths, and the security checks — written to the tester's skill level (**novice / intermediate / expert**, asked up front).
2. **An HTML form** generated from that markdown. Per test: Pass / Fail / Not done, a "what happened" note, a look-and-feel comment with its own severity (a test can pass and still bother the tester), and screenshots by click, drag, or `Ctrl+V`.
3. **A dependency-free helper** — Python *or* Node, whichever the project already uses — that saves progress and, on submit, writes every answer back into the original markdown.

```bash
python docs/uat/tools/uat_server.py docs/uat/UAT-myapp-2026-08-23.md
# or
node docs/uat/tools/uat-server.mjs docs/uat/UAT-myapp-2026-08-23.md
```

Submit is strict — every test answered, every failure explained, every concern rated — with a separate partial-submit path that marks the report as unfinished so nobody mistakes it for a clean run.

**Use it when:** someone outside the codebase has to sign off before release, or you want a repeatable acceptance pass that produces a reviewable artifact instead of a Slack thread.

---

### `processing-uat` — Turn UAT results into a fix plan

Reads a completed UAT and produces a prioritised fix plan. Classifies every failure before proposing anything — a code defect, a *checklist* defect, an environment problem, an out-of-scope test, or a design decision the tester disagrees with all need different fixes. Every entry cites its UAT id, `file:line` evidence, and how to verify the fix.

**Use it when:** a tester has submitted a UAT and you want the findings turned into work rather than a wall of red.

---

### `excalidraw-diagram` — Visual Diagramming

Generates `.excalidraw` JSON files that make **visual arguments**, not just labeled boxes. Produces diagrams where the structure itself communicates meaning — architecture maps, workflow diagrams, data flows, and system overviews that actually teach something.

**Use it when:** you need to visualize an architecture, explain a workflow, or create a diagram that argues a point rather than just listing components.

---

### `intent-engine` — Structured Intent Planning

Converts ambiguous human requests into an explicit contract: structured intent (goal + constraints + success criteria), an executable plan (ordered steps with dependencies), and a verification report. Includes personal intent clarification to understand what *you* are optimizing for.

**Use it when:** you want planning, validation, and escalation instead of one-shot generation. Ideal for complex multi-step tasks where getting the requirements right matters more than starting fast.

---

### `lril` — Second-Brain Workflow Commands

A suite of 19 slash commands (under the `lril:` namespace) that turn ad-hoc prompting into a repeatable **Plan → Implement → Validate** loop, from the Dynamous *claude-code-second-brain* workshop. Prime the agent on a codebase, plan a feature, execute the plan, then review, validate, and commit.

```
/lril:prime           # load codebase context
/lril:plan-feature    # research-backed feature plan
/lril:execute         # run the implementation plan
/lril:code-review     # pre-commit technical review
/lril:commit          # atomic, conventionally-tagged commit
```

Also includes root-cause analysis (`rca`), bug fixing (`implement-fix`), PRD creation (`create-prd`), system review, and a content-ideation suite (`content-linkedin`, `content-x`, `content-youtube`, `content-shorts`, `content-all`).

**Use it when:** you want a disciplined, reviewable engineering workflow instead of one-shot prompts — especially across multi-step features where planning and validation matter.

---

### `port-authhority` — Docker Port Conflict Manager

Detects and resolves port collisions between Docker containers, docker-compose services, and host processes. Scans your environment, identifies conflicts, and suggests fixes — before you hit `address already in use` for the hundredth time.

```
# Automatic detection when you hit port binding errors
# Works with Docker Desktop, docker-compose, and standalone containers
```

**Use it when:** you're deploying containers, running docker-compose, or debugging `EADDRINUSE` / port binding errors.

---

### `context-diet` — Shrink what loads every session

Audits everything that enters context at launch — root and nested `CLAUDE.md`, `.claude/rules/`, resolved `@imports`, `MEMORY.md`, and installed skill descriptions — then moves what is only situationally relevant to a mechanism that loads when it matters. What the codebase already states gets deleted instead of relocated.

```
python skills/context-diet/scripts/discover.py --root .   # measure eager tokens
#   ... review .claude/context-diet-plan.md, then:
python skills/context-diet/scripts/apply.py    --root .   # transactional, with backups
python skills/context-diet/scripts/verify.py   --root .   # nothing lost, every pointer resolves
```

It reports in **eager tokens removed**, not lines deleted — a shorter file that still loads the same content has saved nothing, which is why it never emits `@path` imports. Safety-critical rules stay in root `CLAUDE.md` however situational they are, because only root `CLAUDE.md` is re-injected after `/compact`. Nothing is written without your approval of the plan, and `apply.py` refuses to run against files that changed since they were measured rather than cutting at stale offsets.

**Use it when:** startup context is too full, your `CLAUDE.md` has grown past what anyone reads, or instructions are being ignored because they compete with hundreds of lines of situational detail.

---

## Mirrored from other authors

Installed from this repo alongside the skills above, but authored elsewhere and mirrored verbatim.
Provenance, pinned commit, and license for each are in [`VENDORED.md`](VENDORED.md).

**Planning & design**

| Skill | What it does |
|---|---|
| `codebase-design` | Shared vocabulary for designing deep modules — interfaces that hide more than they expose |
| `domain-modeling` | Pin down domain terminology and ubiquitous language; record the decisions as ADRs |
| `grilling` | Interviews you relentlessly to stress-test a plan before you build it |
| `grill-me` | The interview on its own, for a plan or design already in hand |
| `grill-with-docs` | The same interview, writing ADRs and a glossary as the decisions crystallise |
| `prototype` | Build a throwaway prototype to answer one design question, then throw it away |
| `to-prd` | Turn the current conversation into a PRD on your issue tracker — synthesis, no interview |
| `to-issues` | Break a plan or PRD into independently-grabbable tracer-bullet issues |
| `improve-codebase-architecture` | Scan for deepening opportunities, report them visually, then grill through the ones worth doing |

**Building & debugging**

| Skill | What it does |
|---|---|
| `tdd` | Test-driven development — red, green, refactor, testing behaviour through public interfaces |
| `implement` | Implement a piece of work from a PRD or a set of issues |
| `diagnosing-bugs` | A diagnosis loop for hard bugs and performance regressions |
| `resolving-merge-conflicts` | Work through an in-progress merge or rebase conflict properly |
| `migrate-to-shoehorn` | Migrate test files from `as` assertions to `@total-typescript/shoehorn` |
| `scaffold-exercises` | Create exercise directories with problems, solutions, and explainers that pass linting |

**Process & setup**

| Skill | What it does |
|---|---|
| `triage` | Move issues and external PRs through a state machine of triage roles |
| `handoff` | Compact the current conversation into a handoff document for another agent |
| `ask-matt` | A router over these skills — asks which one fits your situation |
| `setup-matt-pocock-skills` | Configure a repo for the engineering skills: issue tracker, label vocabulary, doc layout |
| `setup-pre-commit` | Husky pre-commit hooks with lint-staged, type checking, and tests |
| `git-guardrails-claude-code` | Hooks that block dangerous git commands (`push --force`, `reset --hard`, `branch -D`) before they run |

**Writing & knowledge**

| Skill | What it does |
|---|---|
| `edit-article` | Restructure sections, sharpen clarity, tighten prose |
| `obsidian-vault` | Search, create, and manage Obsidian notes with wikilinks and index notes |
| `teach` | Teach you a new skill or concept, inside the workspace you're working in |
| `writing-great-skills` | The vocabulary and principles that make a skill predictable — reference for writing skills |

## Installation Options

### Global (available in all projects)

Skills are installed to `~/.claude/skills/` and are available every time you use Claude Code, in any project.

### Project (available only in current project)

Skills are installed to `.claude/skills/` in your current working directory. Useful for sharing specific skills with your team via version control.

### Uninstall

```bash
npx github:seanrobertwright/lril-skills --uninstall
```

### List installed skills

```bash
npx github:seanrobertwright/lril-skills --list
```

## How It Works

Claude Code natively watches two directories for skills:

| Scope | Directory | Visibility |
|-------|-----------|------------|
| Global | `~/.claude/skills/` | All projects, just you |
| Project | `.claude/skills/` | This project, whole team |

The installer copies skill files (each containing a `SKILL.md` with instructions) into the appropriate directory. Claude Code detects them automatically on restart — no plugin registration, no config files, no marketplace accounts.

## Aggregated skills

In addition to the skills authored here, this repo **mirrors curated skills from other authors** so you can install everything from one place. Vendored skills live in `skills/` alongside the originals and are listed in [`VENDORED.md`](VENDORED.md) with their source repo, pinned commit, and license.

How it works:

- **`sources.json`** declares which upstream repos to mirror. Only repos with a redistribution-permitting license (MIT, Apache-2.0, etc.) are included — each vendored skill keeps its upstream `LICENSE` file and a `.vendor.json` provenance marker.
- **`scripts/sync-skills.js`** clones each source, flattens every skill into `skills/<name>/`, and regenerates `VENDORED.md`. Skills authored in this repo are never overwritten.
- **`.github/workflows/sync-skills.yml`** runs the sync on a daily schedule (and on demand) and opens a PR whenever an upstream changes — so updates flow in automatically, with review before they ship.

> Vendored skills are mirrored verbatim and are **not** edited here. Report issues with a vendored skill to its upstream repo (linked in `VENDORED.md`); fixes flow back on the next sync.

**Currently mirrored:** [`mattpocock/skills`](https://github.com/mattpocock/skills) (MIT) — 25 of Matt Pocock's engineering, productivity, and writing skills (TDD, triage, domain modeling, and more).

## Requirements

- **Node.js** >= 18
- **Claude Code** (any recent version)
- Individual skills may have their own dependencies (documented in each skill's instructions). Notably, `creating-uat` ships its helper for both **Python 3.8+** and **Node 18+**, and needs neither `pip install` nor `npm install`.

## Contributing

Have a skill that would be useful to others? PRs welcome. Each skill lives in its own directory under `skills/` and needs at minimum a `SKILL.md` with YAML front matter:

```yaml
---
name: your-skill-name
description: One-line description of when to use this skill.
---

# Your Skill Name

Instructions for Claude go here...
```

Skills authored here live alongside mirrored ones but are never touched by the sync — the sync only overwrites directories carrying a `.vendor.json` marker.

## License

MIT
