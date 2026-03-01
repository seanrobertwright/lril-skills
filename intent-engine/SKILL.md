---
name: intent-engine
description: Use when the user asks to build, run, or integrate an "Intent Engine" that converts user goals into structured intent, executable plans, and verification—now including personal intent clarification.
---

# Intent Engine Skill (Full)

This skill turns ambiguous human requests into an explicit **contract**:

1) **Structured Intent** (goal + inputs + constraints + success + risk + policies)
2) **Executable Plan** (ordered tool steps with dependencies)
3) **Verification Report** (checks + decision: accept/revise/clarify/escalate/refuse)

**Upgrade:** It also clarifies the user’s **Personal Intent** (what they are optimizing for as a programmer/person) before the plan is finalized.

---

## When to use
Use this skill when:
- The user wants a reusable agent “core” that can be shared across domains.
- The user wants planning + validation + escalation instead of one-shot generation.
- The user wants Claude Code / SDK integration via a packaged Skill.

Do NOT use for:
- Simple one-off coding questions where no plan/verification loop is needed.

---

## Output Contract (always)
Return four things:

1) `intent.json` — the structured intent object
2) `plan.json` — ordered steps with dependencies
3) `verification.json` — checks + decision + required clarifications (if any)
4) A brief human-readable summary

All JSON must conform to `resources/intent.schema.json`.

---

## Process

### Step 1 — Compile Domain Intent
Extract and normalize:
- objective (single sentence, canonical)
- domain (e.g., ports, ehs)
- inputs (domain-specific)
- constraints (hard vs soft)
- success criteria
- risk tier (low/medium/high/critical)
- ambiguity_policy and contradiction_policy
- output_format + evidence requirements

Then output `intent.json`.

### Step 1.5 — Clarify Personal Intent (Programmer/Person)
Before planning, infer and/or elicit what the user is optimizing for **right now**.

Populate `intent.personal_intent` with:
- modes: choose 1–2 from: ship, learn, explore, refactor, stabilize, mentor, document, de-risk
- values: 2–5 short phrases (e.g., simplicity, correctness, calm, speed)
- tradeoffs: at least 1 axis (e.g., speed vs correctness) + preference
- anti_goals: 1–3 explicit “do not do” items
- definition_of_done: 3–6 bullets
- energy_budget: low/medium/high
- time_horizon: today/this_week/this_month/long_term
- confidence: 0..1

Rules:
- If confidence < 0.6, set `verification.decision=clarify` and ask **1–3** concise questions BEFORE executing domain actions.
- Never therapize. Keep it practical and engineering-relevant.

Question bank (use sparingly, max 3):
- “Are we optimizing for shipping fast, learning deeply, or reducing risk?”
- “What would make this a win today?”
- “What do you explicitly *not* want (rewrites, yak-shaving, brittle magic)?”
- “Time/energy budget: quick patch, solid fix, or deep refactor?”

Reference: `resources/personal-intent.md`.

### Step 2 — Plan
Create a plan that is:
- Deterministic when possible (parsing, scanning, linting, tests)
- Tool-driven (retrieve, analyze, generate, validate, format)
- Verifiable (each step emits evidence)

Plans MUST use the tool keys defined in `resources/plugin-interface.md` and/or domain plugin specs.

Then output `plan.json`.

### Step 3 — Verify
Verification must check:
- hard constraints satisfied
- evidence present if required
- output format correctness
- contradiction handling respected
- risk-tier gates applied
- **personal intent alignment** (plan matches the user’s mode)

Decision:
- accept: all hard constraints satisfied, success met, no unresolved contradictions
- revise: can fix automatically without new info
- clarify: missing info or contradictions require user input
- escalate: high/critical risk requires human review or ambiguity is too dangerous
- refuse: disallowed or unsafe request

Then output `verification.json`.

---

## Domain plugins
Domain plugins live under `resources/plugins/`.

- ports: `resources/plugins/ports.plugin.md`
- ehs: `resources/plugins/ehs.plugin.md`

Plugins define:
- default constraints
- planning templates (step sequences)
- validator checklists
- clarification/escalation triggers
- personal-intent mapping (how mode changes the plan)

---

## Examples
See:
- `resources/intent-examples.md`
