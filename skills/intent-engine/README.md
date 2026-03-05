# Intent Engine

A Claude Code Skill that translates human goals into structured, machine-actionable
intent specs with goal hierarchies, verification hooks, escalation logic, and
audit trails.

## What It Does

1. **Structured Intent** -- parses IntentSpec markdown into executable contracts
2. **Goal Hierarchy** -- explicit priority ordering for conflict resolution
3. **Verification Hooks** -- runnable commands that prove success criteria are met
4. **Escalation Logic** -- explicit triggers for when to stop and ask a human
5. **Personal Intent** -- aligns plans with what the user is optimizing for
6. **Session Reinforcement** -- compaction-resistant anchors survive context loss
7. **Intent Versioning** -- semantic versioning tracks how intents evolve

## Files

- `SKILL.md` -- Claude Skill entrypoint (instructions + contract)
- `resources/intent.schema.json` -- JSON Schema for the output contract
- `resources/templates/` -- IntentSpec templates (minimal, full, goal hierarchy)
- `resources/plugin-interface.md` -- Domain plugin contract + tool keys
- `resources/domain-catalog.md` -- Domains overview
- `resources/intent-examples.md` -- Examples including personal intent
- `resources/personal-intent.md` -- Personal intent reference
- `resources/plugins/*.plugin.md` -- Domain plugin specs (ports, ehs)
- `scripts/intent_compile.py` -- Parse IntentSpec markdown into JSON
- `scripts/intent_validate.py` -- Validate contracts and run verification commands
- `scripts/run_intent_engine.py` -- Full compile -> plan -> verify cycle
- `scripts/generate_claude_md.py` -- Generate CLAUDE.md with intent architecture

## Quick Start

Parse a spec file:
```bash
python scripts/intent_compile.py .intents/my-task.md
```

From freeform text:
```bash
echo "Fix my port conflicts" | python scripts/intent_compile.py --stdin
```

Full engine cycle:
```bash
python scripts/run_intent_engine.py .intents/my-task.md --run-checks --audit
```

Validate a contract:
```bash
python scripts/intent_validate.py contract.json --run-checks --audit
```

Generate a CLAUDE.md with intent architecture:
```bash
python scripts/generate_claude_md.py --preset ehs -o CLAUDE.md
python scripts/generate_claude_md.py --from-spec .intents/my-task.md
python scripts/generate_claude_md.py  # interactive mode
```

## IntentSpec Format

Minimal:
```markdown
---
intent: fix-checkout
version: "1.0.0"
priority: high
---
# IntentSpec: Fix Checkout Bug
**Objective:** Payment step has 23% drop-off rate
**Success:** Drop-off rate < 5%
**Constraint:** Must not break saved payment methods
**Verify:** `npm run test:e2e`
```

See `resources/templates/` for full templates.
