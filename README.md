<p align="center">
  <img src="assets/logo.svg" alt="LRIL Skills" width="820">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-1.0.0-blue?style=flat-square" alt="Version">
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="License">
  <img src="https://img.shields.io/badge/node-%3E%3D18-brightgreen?style=flat-square" alt="Node">
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey?style=flat-square" alt="Platform">
</p>

<p align="center">
  <strong>Production-grade skills for Claude Code that handle the work you shouldn't have to think about.</strong>
  <br>
  Browser automation, end-to-end testing, visual diagramming, intent planning, and Docker port management — installed in seconds.
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

## Skills

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

### `excalidraw-diagram` — Visual Diagramming

Generates `.excalidraw` JSON files that make **visual arguments**, not just labeled boxes. Produces diagrams where the structure itself communicates meaning — architecture maps, workflow diagrams, data flows, and system overviews that actually teach something.

**Use it when:** you need to visualize an architecture, explain a workflow, or create a diagram that argues a point rather than just listing components.

---

### `intent-engine` — Structured Intent Planning

Converts ambiguous human requests into an explicit contract: structured intent (goal + constraints + success criteria), an executable plan (ordered steps with dependencies), and a verification report. Includes personal intent clarification to understand what *you* are optimizing for.

**Use it when:** you want planning, validation, and escalation instead of one-shot generation. Ideal for complex multi-step tasks where getting the requirements right matters more than starting fast.

---

### `port-authhority` — Docker Port Conflict Manager

Detects and resolves port collisions between Docker containers, docker-compose services, and host processes. Scans your environment, identifies conflicts, and suggests fixes — before you hit `address already in use` for the hundredth time.

```
# Automatic detection when you hit port binding errors
# Works with Docker Desktop, docker-compose, and standalone containers
```

**Use it when:** you're deploying containers, running docker-compose, or debugging `EADDRINUSE` / port binding errors.

---

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

## Requirements

- **Node.js** >= 18
- **Claude Code** (any recent version)
- Individual skills may have their own dependencies (documented in each skill's instructions)

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

## License

MIT
