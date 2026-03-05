---
domain: ports
version: 0.1
risk_default: low
---

# Ports Plugin (Intent Engine)

## What this plugin does
Takes a request like “fix port conflicts” or “reserve ports by category” and produces:
- a deterministic allocation plan
- updated compose/dev config
- a reservations file (source of truth)
- validation that collisions are eliminated

## Domain inputs (suggested)
- compose_path: string (path to docker-compose.yml)
- category_ranges: object (e.g., {"db":[3000,3999], "ui":[4000,4999], "api":[5000,5999], "tools":[6000,6999]})
- reservation_path: string (e.g., .ports/reservations.json)
- allocation_policy: "deterministic" | "best_available"
- preserve_existing: bool
- allow_random: bool (default false)

## Default constraints
Hard:
- no_collisions = true
- respect_category_ranges = true
- persist_reservations = true

Soft:
- preserve_existing_mappings = true (if preserve_existing)

## Planning template (typical steps)
1) parse_compose
2) scan_host_ports
3) allocate_ports
4) write_compose
5) write_reservations
6) validate_no_collisions

## Validators (checklist)

### Required
- V1: compose parsed successfully
- V2: collisions = 0 after write
- V3: all assigned ports within category ranges (when provided)
- V4: reservations file written and matches compose
- V5: deterministic mapping stable when rerun with same inputs (if allocation_policy=deterministic)

### Nice-to-have
- N1: minimal changes (diff minimized) if preserve_existing=true
- N2: produces a summary table of mappings

## Clarification triggers
Return decision=clarify when:
- compose_path missing or invalid
- category cannot be inferred for services and no mapping provided
- ranges overlap or are invalid

## Auto-revise triggers
Return decision=revise when:
- collisions remain but can be resolved by choosing next free port in range
- reservations mismatch compose but can be reconciled

## Risk inference
- low: read/plan only
- medium: writing files in repo or changing port mappings for running stacks

## Goal Hierarchy Overrides

When the ports domain plugin is active, the default goal hierarchy is overridden:

1. **No collisions** -- zero port conflicts in the running stack
2. **Deterministic allocation** -- same inputs always produce same port assignments
3. **Backward compatibility** -- preserve existing port mappings when possible
4. **Correctness** -- validation passes; reservations match compose
5. **Developer experience** -- clear mappings, easy onboarding

### Domain-Specific Conflict Resolution
- **Collision vs. Preservation**: Resolve collision first; log which mapping changed.
- **Category range conflict**: Ask before reassigning ports across categories.
- **Config drift detected**: Reconcile reservations file with docker-compose state.
- **Minimal diff vs. Clean allocation**: Prefer minimal diff unless collisions persist.

## Verification Commands

Domain-specific verification commands for ports intents:

- `python scripts/validate_no_collisions.py` -- Check for duplicate host port bindings
- `python scripts/check_reservations.py` -- Verify reservations file matches compose
- `docker compose config --quiet` -- Validate compose file syntax
- `python scripts/check_category_ranges.py` -- Verify ports are within declared ranges

These are suggested defaults. Individual IntentSpecs should override with
task-specific commands in their `### Verification` section.

## Personal intent mapping
- ship:
  - minimize diffs; preserve existing mappings when possible
  - skip nice-to-have validators unless collisions persist
- learn:
  - include a short “port allocation rationale” artifact
  - show before/after mapping table
- stabilize:
  - add rerun validation: rescan and confirm no collisions
  - add reservations consistency check
- refactor:
  - propose category tagging and a tidier reservations schema upgrade
