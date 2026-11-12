<p align="center">
  <img src="assets/logo.svg" alt="LRIL Skills" width="820">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-1.0.0-blue?style=flat-square" alt="Version">
  <img src="https://img.shields.io/badge/skills-40-blueviolet?style=flat-square" alt="Skills">
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="License">
  <img src="https://img.shields.io/badge/node-%3E%3D18-brightgreen?style=flat-square" alt="Node">
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey?style=flat-square" alt="Platform">
</p>

<p align="center">
  <strong>Production-grade skills for Claude Code that handle the work you shouldn't have to think about.</strong>
  <br>
  Browser automation, end-to-end testing, acceptance testing, visual diagramming, intent planning, and
  Docker port management — plus 27 mirrored skills, from engineering to diagrams and logo design. Installed in seconds.
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

**40 skills** — 13 authored here, 27 mirrored from other authors.

| | |
|---|---|
| **Testing & QA** | [`agent-browser`](#agent-browser--browser-automation) · [`e2e-test`](#e2e-test--end-to-end-testing) · [`creating-uat`](#creating-uat--user-acceptance-testing) · [`processing-uat`](#processing-uat--turn-uat-results-into-a-fix-plan) · [`test-sweet`](#test-sweet--only-the-tests-each-build-step-needs) · `tdd` · `diagnosing-bugs` |
| **Planning & design** | [`intent-engine`](#intent-engine--structured-intent-planning) · [`how-its-made`](#how-its-made--how-a-repo-was-built) · `codebase-design` · `domain-modeling` · `grilling` · `prototype` · `to-prd` · `to-issues` |
| **Workflow** | [`lril`](#lril--second-brain-workflow-commands) · [`ask-sean`](#ask-sean--which-skill-and-whats-next) · [`help-me`](#help-me--a-follow-along-checklist-for-a-task-you-do-not-understand) · `implement` · `triage` · `handoff` · `resolving-merge-conflicts` |
| **Environment** | [`port-authhority`](#port-authhority--docker-port-conflict-manager) · [`context-diet`](#context-diet--shrink-what-loads-every-session) · `setup-pre-commit` · `git-guardrails-claude-code` |
| **Communication** | [`excalidraw-diagram`](#excalidraw-diagram--visual-diagramming) · `edit-article` · `teach` · `obsidian-vault` · `reladraw` · `logo-design` |

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

### `ask-sean` — Which skill, and what's next

The `ask-matt` router, taken from a newer upstream revision than the copy mirrored here (so it routes through `to-spec`, `to-tickets`, `wayfinder` and `research`, which this repo does not ship yet), with one addition: ask it what to work on next and it reads the project's actual state (branch, unpushed work, open PRs, open and blocked tickets, the progress record), recommends one step, and hands back a prompt to paste into a fresh session. The prompt sits under a `Prompt =` label in a fenced block with no language tag, which Claude Code draws in its accent color; it is the only colored text in the reply, so it is plain what to copy.

```
/ask-sean what's next?
```

**Use it when:** you've finished a ticket and want the next one queued up as a ready-to-paste prompt, or you're unsure which skill fits the situation.

Adapted from [`ask-matt`](https://github.com/mattpocock/skills) by Matt Pocock (MIT); the upstream license is kept in `skills/ask-sean/LICENSE`.

---

### `how-its-made` — How a repo was built

Give it a GitHub repo and it works out how the thing was built: spec-driven or test-driven, SpecKit or OpenSpec or BMAD, which agents, skills, and MCPs. It reads the commit history, the file tree, and a sample of pull requests, then produces three files from one JSON source:

1. **A Markdown report** with the story of how the process evolved, a classification for each era of the repo, the practices worth copying and what each costs to adopt, and the blind spots.
2. **An HTML page** of the same report, with an **animated SVG diagram** of the current development workflow. It works offline, and it stops animating for readers who prefer reduced motion.
3. **The JSON** both are rendered from, so the two can never disagree.

```
How was https://github.com/acme/widget built?
```

Every finding is labelled by what it has earned: **Present** (the file exists), **Used** (the history shows it exercised), or **Enforced** (CI or a hook requires it). A leftover `.specify/` folder never reads as adoption, and test files alone never read as TDD. Indirect signs of AI use stay in a separate hedged section and never feed the classification.

The target repo is treated as hostile, because its agent files are written to instruct agents. It is cloned with nothing checked out, nothing from it is run, and the clone is deleted at the end. The report closes with a section mapping each practice to the skills you already have, kept separate so the rest stays shareable.

**Use it when:** you want to learn from how someone else builds, or to see which of their practices you are missing.

---

### `test-sweet` — Only the tests each build step needs

Point it at a plan, spec, PRD, set of GitHub issues, or tickets folder. It writes a test plan that gives every build step only the tests it needs, then writes a step's tests first when you build that step.

Every test carries a **warrant**: a promise the source makes for that step, or a serious risk (lost data, money, security and login, privacy, anything that cannot be undone, plus whatever you name as worst-if-broke). A candidate with no warrant is cut, and the plan records each cut with its reason. A promise only a person can check, such as a manual checklist run, is listed as a by-hand check. A step that promises nothing testable is recorded as "no tests needed".

```
/test-sweet docs/plan.md
/test-sweet step 2
```

The plan is saved to `test-sweet/` in your project and waits for your approval before any test is written. Each test gets the cheapest level that would catch the bug: unit, integration, or end-to-end. Building a step hands its test list to the `tdd` skill when that is installed, and runs its own red-green loop when it is not. It works on any language and reads the project to find the test runner already in use.

**Use it when:** you have a build plan and want a test suite that covers what matters and nothing else. A source with no build steps is sent to a planning skill first.

---

### `help-me` — A follow-along checklist for a task you do not understand

For when Claude has told you to do something and you do not know what it means. It rewrites the task as a checklist web page for someone who is not a programmer, and opens the page in your browser.

```
/help-me I don't understand the instructions you just gave me
/help-me issue 494
/help-me 494
/help-me continue
```

With no number it uses the most recent thing in the conversation that asked you to do something. With a number it reads that GitHub issue in the current repo through `gh` and walks you through getting it done.

Each step is one action: where to look, what to click or type, what you should see afterwards, and what to do if you do not. Anything you need to type has a **Copy** button. Point at a step, or press its **Why?** button, for an everyday explanation of why the step is there. Tick the steps as you go; the page remembers your ticks. If a step does not go the way it says, **I'm stuck on this step** copies a message to paste back to Claude, which then rewrites that step.

Ask for help with a task that already has an unfinished checklist and it does not build a second one. It re-checks the existing checklist against the task as it stands now, shows you any improvements it found in plain words, and asks which ones you want. Only the ones you pick are added.

You do not have to finish in one sitting. Press **Save my progress**, close the page, and type `/help-me continue` later, even in a new conversation. It lists the checklists you have not finished, lets you pick one, and opens it with your ticks in place. A checklist leaves that list once you tell Claude you have finished it and Claude has checked the result.

Each checklist is a single page kept in a `.help-me` folder in your home directory, outside your project. Nothing is installed and nothing is left running. Your ticks live in your web browser, so they come back in the same browser on the same computer.

**Use it when:** you have been given steps you cannot follow, or you want to be walked through an issue one small action at a time.

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

**Visual design**

| Skill | What it does |
|---|---|
| `reladraw` | Architecture and data-flow diagrams in a text language where you state the arrangement (`right of api`, `level with queue`), so Claude can read the layout back from the source; renders to standalone SVG |
| `logo-design` | Logos and brand marks from brief to production SVGs: concepts, 16 px and one-colour tests, client presentation boards, favicon and app-icon exports, and a searchable library of 1,400+ real-world logos for reference |

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

- **`sources.json`** declares which upstream repos to mirror. Only repos with a redistribution-permitting license (MIT, Apache-2.0, etc.) are included — each vendored skill keeps its upstream `LICENSE` file (and `NOTICE`, when upstream has one) and a `.vendor.json` provenance marker.
- **`scripts/sync-skills.js`** clones each source, flattens every skill into `skills/<name>/`, and regenerates `VENDORED.md`. Skills authored in this repo are never overwritten.
- **`.github/workflows/sync-skills.yml`** runs the sync on a daily schedule (and on demand) and opens a PR whenever an upstream changes — so updates flow in automatically, with review before they ship.

> Vendored skills are mirrored verbatim and are **not** edited here. Report issues with a vendored skill to its upstream repo (linked in `VENDORED.md`); fixes flow back on the next sync.

**Currently mirrored:**

- [`mattpocock/skills`](https://github.com/mattpocock/skills) (MIT) — 25 of Matt Pocock's engineering, productivity, and writing skills (TDD, triage, domain modeling, and more).
- [`kaankiziltug/logo-design-skill`](https://github.com/kaankiziltug/logo-design-skill) (MIT) — `logo-design`, a logo and brand-mark design skill.
- [`reladraw/reladraw`](https://github.com/reladraw/reladraw) (Apache-2.0) — `reladraw`, the skill that ships with the reladraw diagram language.

## Requirements

- **Node.js** >= 18
- **Claude Code** (any recent version)
- Individual skills may have their own dependencies (documented in each skill's instructions). Notably, `how-its-made` needs `git` and **Node 18+**, and uses an authenticated `gh` for pull request evidence when it is available. `help-me` needs **Node 18+**, and an authenticated `gh` when you give it an issue number. `creating-uat` ships its helper for both **Python 3.8+** and **Node 18+**, and needs neither `pip install` nor `npm install`. `logo-design` runs dependency-free **Python 3** scripts; turning SVGs into PNGs needs one renderer on the machine (cairosvg, rsvg-convert, Inkscape, or headless Chrome/Chromium). `reladraw` needs the `reladraw` CLI (`npm install -g reladraw`, or `npx reladraw` without installing).

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
