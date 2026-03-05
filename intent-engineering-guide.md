# Intent Engineering: A Comprehensive Research Guide
**The Evolution from Prompt → Context → Intent in Agentic AI Development**

> *Compiled March 2026 — Research synthesis for AI-assisted coding workflows and Claude Code Skills development*

---

## Table of Contents

1. [What Is Intent Engineering?](#what-is-intent-engineering)
2. [The Three-Layer Evolution](#the-three-layer-evolution)
3. [Why This Matters for Developers](#why-this-matters-for-developers)
4. [Intent Engineering in Daily Coding](#intent-engineering-in-daily-coding)
5. [Integration with Context Engineering](#integration-with-context-engineering)
6. [The IntentSpec Format](#the-intentspec-format)
7. [Implementation Patterns & Code Examples](#implementation-patterns--code-examples)
8. [Claude Code Skills & the lril-skills Repository](#claude-code-skills--the-lril-skills-repository)
9. [Evaluating & Improving the Intent-Engine Skill](#evaluating--improving-the-intent-engine-skill)
10. [Improved SKILL.md Template](#improved-skillmd-template)
11. [Key Takeaways](#key-takeaways)

---

## What Is Intent Engineering?

Intent engineering is the discipline of transforming strategic human goals into **explicit, machine-actionable specifications** that autonomous AI agents can execute, verify, and be held accountable to — over time, not just in a single moment.

It is *not*:
- Writing better prompts
- Optimizing system instructions
- Mission statements or aspirational goals

It *is*:
- Machine-readable goal hierarchies with decision priorities
- Conflict resolution protocols (e.g., speed vs. quality — which wins?)
- Verifiable, auditable guardrails and behavioral boundaries
- Feedback loops that close the gap between AI outputs and actual business outcomes

The term has gained significant traction in early 2025–2026 as AI agents move from assistants to autonomous actors embedded in real systems — where a drift toward easily measurable goals (like response speed) over harder-to-measure goals (like trust and retention) can quietly erode business value.

---

## The Three-Layer Evolution

The clearest framework for understanding intent engineering is the three-layer stack. Each layer solved a real problem — and exposed the limits of the one before it.

```
┌─────────────────────────────────────────────────┐
│  INTENT ENGINEERING                              │
│  "What should the AI optimize for over time?"   │
│  → Decision hierarchies, guardrails, trade-offs  │
├─────────────────────────────────────────────────┤
│  CONTEXT ENGINEERING                             │
│  "What does the AI know and can access?"        │
│  → RAG, memory, tools, CLAUDE.md, Skills        │
├─────────────────────────────────────────────────┤
│  PROMPT ENGINEERING                              │
│  "What should the AI do right now?"             │
│  → Instructions, examples, chain-of-thought     │
└─────────────────────────────────────────────────┘
```

### Layer 1: Prompt Engineering (2022–2024)
Prompt engineering taught us to craft precise instructions for a single interaction. It works well when a human reviews every output. It breaks down the moment AI is embedded in autonomous workflows, because it only defines **what to do in this moment**.

### Layer 2: Context Engineering (2024–2025)
Context engineering added the information layer — everything an agent needs to **understand the world it operates in**: retrieval-augmented generation (RAG), vector databases, tool access, CLAUDE.md files, Skills, and long-term memory buffers.

Anthropic's own research defines context engineering as managing the entire context state across system instructions, tools, Model Context Protocol (MCP), external data, and message history. Claude Code's `/compact` command, lazy-loaded Skills, and just-in-time file retrieval are all context engineering primitives.

### Layer 3: Intent Engineering (2025–Present)
Even with perfect context, an AI agent can optimize for the wrong thing. Intent engineering defines **what the agent should be optimizing for** — and what happens when goals conflict.

> *"Context engineering tells the agent what it knows and can access. Intent engineering tells the agent what it should be optimizing for over time."*
> — Faisal Feroz, CTO/Technical Architect

---

## Why This Matters for Developers

The Klarna AI case is instructive. Their assistant handled 2.3 million conversations in one month, reduced resolution time from 11 minutes to under 2 minutes, and projected $40M in profit improvement. Yet optimizing for conversation speed — a single, easily measurable metric — can quietly erode harder-to-measure values like customer trust and long-term retention.

For developers and EH&S safety systems, the parallel is direct: an AI agent told only to "resolve safety tickets efficiently" might start cutting corners on documentation completeness or regulatory cross-referencing. **Intent engineering is how you prevent that drift.**

Key questions intent engineering forces you to answer:
- When speed conflicts with thoroughness, which wins?
- What behaviors are mandatory versus optional?
- When should the AI escalate to a human?
- How do you measure alignment with actual goals over time?

---

## Intent Engineering in Daily Coding

### Practical Shift #1: From Vague Prompts to Intent Specs

**Before (Prompt Engineering):**
```
Fix the checkout bug and make it faster.
```

**After (Intent Engineering):**
```markdown
## Intent Spec: Checkout Reliability Fix

**Objective:** Users are abandoning checkout at the payment step (observed: 23% drop-off
in analytics, confirmed by 4 support tickets this week). This is costing ~$8K/day in
lost revenue.

**User Goal:** Complete a purchase in under 3 steps without encountering errors.

**Outcomes (verifiable):**
- Payment step drop-off rate < 5% (measured via analytics event: checkout_abandoned)
- Page load time < 800ms on 3G connection
- Zero uncaught exceptions in payment flow for 7 consecutive days

**Constraints:**
- Must not break existing saved payment method behavior
- Stripe API version must remain pinned at 2023-10-16
- All changes must pass existing E2E test suite

**Edge Cases:**
- User has expired card on file
- Network timeout during payment processing
- User navigates back during 3DS authentication

**Priority if conflicts arise:** Reliability > Speed > Feature completeness
```

### Practical Shift #2: Define Decision Hierarchies in CLAUDE.md

Instead of letting the agent decide what matters most, make priorities explicit:

```markdown
# Project Intent Architecture

## Goal Hierarchy (in order of priority)
1. **Safety & Compliance**: Never generate code that bypasses auth checks, skips
   validation, or removes error handling to improve performance.
2. **Correctness**: Passing tests > passing linting > code elegance.
3. **Performance**: Optimize only after correctness is verified.
4. **Developer Experience**: Readable code preferred over clever one-liners.

## Conflict Resolution Rules
- If speed vs. safety conflict: always choose safety, flag the trade-off in comments.
- If scope creep is detected: complete the stated task, then add a TODO comment
  proposing the expansion. Do not silently expand scope.
- If ambiguous requirements: ask one clarifying question before proceeding.

## Escalation Triggers
Pause and ask a human before:
- Deleting any data (even test data)
- Modifying authentication/authorization logic
- Changing any environment variable or config file
- Making more than 5 file changes for a task estimated at 1-2 files
```

### Practical Shift #3: Structured Verification Criteria

Intent engineering requires that "done" be machine-verifiable, not just human-readable.

```python
# intent_verifier.py — validate AI outputs against intent spec

import json
from dataclasses import dataclass
from typing import List, Callable

@dataclass
class IntentCriteria:
    name: str
    description: str
    check: Callable[[], bool]
    weight: float = 1.0  # for weighted scoring

class IntentVerifier:
    def __init__(self, intent_name: str):
        self.intent_name = intent_name
        self.criteria: List[IntentCriteria] = []

    def add_criterion(self, name: str, description: str,
                      check: Callable, weight: float = 1.0):
        self.criteria.append(IntentCriteria(name, description, check, weight))
        return self

    def verify(self) -> dict:
        results = []
        total_weight = sum(c.weight for c in self.criteria)
        weighted_score = 0

        for criterion in self.criteria:
            passed = criterion.check()
            weighted_score += criterion.weight if passed else 0
            results.append({
                "criterion": criterion.name,
                "description": criterion.description,
                "passed": passed,
                "weight": criterion.weight
            })

        overall_score = weighted_score / total_weight if total_weight > 0 else 0

        return {
            "intent": self.intent_name,
            "score": round(overall_score, 3),
            "passed": overall_score >= 0.8,  # 80% threshold
            "criteria": results
        }


# Usage example for a checkout fix intent
def verify_checkout_intent():
    import subprocess, requests

    verifier = IntentVerifier("checkout-reliability-fix")

    # Add verifiable criteria from the intent spec
    verifier.add_criterion(
        name="e2e_tests_pass",
        description="All existing E2E tests pass",
        check=lambda: subprocess.run(
            ["npm", "run", "test:e2e"], capture_output=True
        ).returncode == 0,
        weight=2.0  # critical — higher weight
    )

    verifier.add_criterion(
        name="no_auth_bypasses",
        description="No authentication checks removed",
        check=lambda: not any(
            "// auth bypass" in open(f).read()
            for f in ["src/checkout.js", "src/payment.js"]
            if __import__("os").path.exists(f)
        ),
        weight=3.0  # safety — highest weight
    )

    verifier.add_criterion(
        name="performance_target",
        description="Page load < 800ms",
        check=lambda: True,  # Replace with real Lighthouse/WebPageTest API call
        weight=1.0
    )

    return verifier.verify()
```

---

## Integration with Context Engineering

Intent engineering and context engineering are **complementary layers**, not competing approaches. Here's how they interact in a Claude Code workflow:

```
┌──────────────────────────────────────────────────────────────┐
│                    Agent Session Start                       │
├──────────────────────────────────────────────────────────────┤
│  CONTEXT LAYER (loaded at session start)                     │
│  ├── CLAUDE.md → project conventions, architecture           │
│  ├── Skills (lazy-loaded) → specialized capabilities         │
│  ├── MCP servers → external tool access                      │
│  └── RAG / file search → codebase knowledge                  │
├──────────────────────────────────────────────────────────────┤
│  INTENT LAYER (governs behavior across the session)          │
│  ├── Goal hierarchy → what matters most                      │
│  ├── Decision rules → how to resolve conflicts               │
│  ├── Guardrails → what is forbidden                          │
│  └── Escalation triggers → when to pause and ask            │
├──────────────────────────────────────────────────────────────┤
│  PROMPT LAYER (per-task)                                     │
│  ├── Intent spec → structured task definition                │
│  ├── Examples → few-shot demonstrations                      │
│  └── Format constraints → output structure                   │
└──────────────────────────────────────────────────────────────┘
```

### The Four Context Engineering Strategies (Anthropic Research)

Anthropic's engineering blog identifies four strategies for managing context — all of which can carry intent information:

| Strategy | What It Does | Intent Engineering Hook |
|----------|-------------|------------------------|
| **Write** | Save information outside context window | Persist goal hierarchy in NOTES.md |
| **Select** | Pull relevant info into context on demand | Load relevant intent specs via Skills |
| **Compress** | Summarize history to preserve critical context | Retain decision rules during compaction |
| **Isolate** | Spawn sub-agents with focused context | Give each sub-agent a specific intent slice |

### CLAUDE.md as the Intent Anchor

The `CLAUDE.md` file is the single most impactful place to embed both context and intent:

```markdown
# CLAUDE.md — Project Context + Intent Architecture

## Project Context
- Stack: Python 3.12, FastAPI, PostgreSQL, Redis
- Testing: pytest + coverage threshold 85%
- Deployment: Docker → Kubernetes via GitHub Actions

## Intent Architecture

### Mission
Build reliable, auditable EH&S management tools that safety professionals
can trust with regulatory compliance data.

### Goal Hierarchy (enforced, not suggested)
1. Regulatory accuracy (OSHA/EPA citations must be verified)
2. Data integrity (never modify records without audit trail)
3. Correctness (passing tests before merging)
4. Performance (optimize after correctness)

### Decision Rules
- **Accuracy vs Speed**: Always choose accuracy.
- **Completeness vs Scope**: Complete stated task first; propose expansions separately.
- **Ambiguity**: Ask before assuming, especially for compliance-related logic.

### Hard Guardrails (never do these)
- Do not remove try/except blocks around database writes
- Do not skip audit logging for any data modification
- Do not add admin backdoors or bypass authentication
- Do not change regulatory citation text without verification

### Escalation Criteria
Stop and ask before:
- Any schema migration affecting production data
- Disabling any safety check or validation rule
- Adding new external API integrations
```

---

## The IntentSpec Format

Based on research from Pathmode and emerging industry practice, a structured **IntentSpec** format has become the gold standard for translating human goals into agent-executable tasks.

```markdown
---
intent: <short-slug>
version: 1.0
priority: critical | high | medium | low
---

## IntentSpec: <Title>

### Objective
<!-- What user problem are you solving? Ground it in evidence. -->
[Support ticket / metric / user quote that motivated this]

### User Goal
<!-- The job-to-be-done from the user's perspective. -->
As a [user type], I need to [accomplish X] so that [outcome Y].

### Outcomes (Verifiable)
<!-- Observable, measurable state changes. These become your test criteria. -->
- [ ] Metric A moves from X to Y (measured via [method])
- [ ] Feature B behaves like [specific behavior] in [specific scenario]
- [ ] Error rate for C drops below D% for 7 consecutive days

### Constraints
<!-- What must not change. The guardrails. -->
- Must maintain backward compatibility with [API version / data schema]
- Must not increase p95 latency above [threshold]
- Must pass existing test suite without modifications to tests

### Edge Cases
<!-- Scenarios where intent could be misinterpreted or go wrong. -->
- When [condition]: [expected behavior]
- When [condition]: [escalate to human / fail gracefully]

### Conflict Resolution
<!-- If this intent conflicts with project goal hierarchy, resolution rule. -->
If speed vs. accuracy conflict: accuracy wins. Flag trade-off in PR description.

### Verification
<!-- How do you know the agent succeeded? -->
- Automated: `npm run test:e2e` passes
- Manual: QA checklist item #12 confirmed
- Metric: Analytics event [checkout_completed] rate > 95% for 3 days
```

---

## Implementation Patterns & Code Examples

### Pattern 1: Intent-Aware Agent Router

```python
# intent_router.py — routes tasks to appropriate agents based on intent
from enum import Enum
from dataclasses import dataclass
from typing import Optional
import anthropic

class IntentPriority(Enum):
    SAFETY = 1      # EH&S compliance, auth, data integrity
    CORRECTNESS = 2 # Tests pass, logic is right
    PERFORMANCE = 3 # Speed, efficiency
    EXPERIENCE = 4  # Developer ergonomics, readability

@dataclass
class Intent:
    description: str
    priority: IntentPriority
    requires_human_approval: bool = False
    forbidden_patterns: list[str] = None
    verification_command: Optional[str] = None

    def to_system_prompt_fragment(self) -> str:
        guardrails = ""
        if self.forbidden_patterns:
            guardrails = "\n\nFORBIDDEN patterns (never do these):\n" + \
                         "\n".join(f"- {p}" for p in self.forbidden_patterns)

        approval_note = ""
        if self.requires_human_approval:
            approval_note = "\n\nSTOP and request human approval before proceeding."

        return f"""
## Active Intent: {self.description}
Priority Level: {self.priority.name}
{guardrails}
{approval_note}
""".strip()


class IntentAwareAgent:
    """An agent that embeds intent specifications into every request."""

    def __init__(self, base_intent: Intent):
        self.base_intent = base_intent
        self.client = anthropic.Anthropic()

    def execute(self, task: str, additional_context: str = "") -> str:
        system_prompt = f"""You are an expert software engineer working on a
safety-critical codebase.

{self.base_intent.to_system_prompt_fragment()}

## Additional Context
{additional_context}

Always verify your output against the intent before responding.
If you detect a conflict between the task and the intent priority,
call it out explicitly."""

        response = self.client.messages.create(
            model="claude-opus-4-6",
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": task}]
        )
        return response.content[0].text


# Example: EH&S safety-critical intent
ehs_intent = Intent(
    description="OSHA compliance code changes must never remove safety checks",
    priority=IntentPriority.SAFETY,
    requires_human_approval=True,
    forbidden_patterns=[
        "Removing try/except from regulatory data writes",
        "Bypassing audit log insertion",
        "Hardcoding regulatory thresholds",
        "Skipping OSHA citation validation"
    ],
    verification_command="pytest tests/compliance/ -v --tb=short"
)

agent = IntentAwareAgent(ehs_intent)
```

### Pattern 2: Intent Spec Parser for Claude Code

```python
# parse_intent.py — parse IntentSpec markdown files for use in agent prompts
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class ParsedIntentSpec:
    intent_id: str
    title: str
    objective: str
    user_goal: str
    outcomes: list[str]
    constraints: list[str]
    edge_cases: list[str]
    conflict_resolution: str
    verification: list[str]
    priority: str = "medium"

    def to_agent_prompt(self) -> str:
        """Convert spec to a structured agent prompt."""
        outcomes_str = "\n".join(f"  - {o}" for o in self.outcomes)
        constraints_str = "\n".join(f"  - {c}" for c in self.constraints)
        edge_cases_str = "\n".join(f"  - {e}" for e in self.edge_cases)

        return f"""
## Task Intent: {self.title}
Priority: {self.priority.upper()}

**Objective:** {self.objective}

**User Goal:** {self.user_goal}

**Required Outcomes (your success criteria):**
{outcomes_str}

**Hard Constraints (never violate these):**
{constraints_str}

**Edge Cases to handle:**
{edge_cases_str}

**If goals conflict:** {self.conflict_resolution}
""".strip()


def parse_intent_spec(filepath: str) -> ParsedIntentSpec:
    """Parse a markdown IntentSpec file into a structured object."""
    content = Path(filepath).read_text()

    def extract_section(name: str) -> str:
        pattern = rf"### {name}\s*\n(.*?)(?=\n###|\Z)"
        match = re.search(pattern, content, re.DOTALL)
        return match.group(1).strip() if match else ""

    def extract_list(section_content: str) -> list[str]:
        items = re.findall(r"^[-*]\s+(.+)$", section_content, re.MULTILINE)
        checkboxes = re.findall(r"^\[.\]\s+(.+)$", section_content, re.MULTILINE)
        return items + checkboxes

    # Extract frontmatter
    fm_match = re.match(r"---\n(.*?)\n---", content, re.DOTALL)
    frontmatter = {}
    if fm_match:
        for line in fm_match.group(1).split("\n"):
            if ":" in line:
                k, v = line.split(":", 1)
                frontmatter[k.strip()] = v.strip()

    # Extract title
    title_match = re.search(r"## IntentSpec: (.+)", content)
    title = title_match.group(1) if title_match else "Untitled"

    objective_content = extract_section("Objective")
    user_goal_content = extract_section("User Goal")
    outcomes_content = extract_section("Outcomes")
    constraints_content = extract_section("Constraints")
    edge_cases_content = extract_section("Edge Cases")
    conflict_content = extract_section("Conflict Resolution")
    verification_content = extract_section("Verification")

    return ParsedIntentSpec(
        intent_id=frontmatter.get("intent", "unknown"),
        title=title,
        objective=objective_content,
        user_goal=user_goal_content,
        outcomes=extract_list(outcomes_content),
        constraints=extract_list(constraints_content),
        edge_cases=extract_list(edge_cases_content),
        conflict_resolution=conflict_content,
        verification=extract_list(verification_content),
        priority=frontmatter.get("priority", "medium")
    )
```

### Pattern 3: Intent-Aware CLAUDE.md Generator

```python
# generate_claude_md.py — generate project CLAUDE.md with embedded intent layer
from pathlib import Path
from typing import List, Optional

def generate_claude_md(
    project_name: str,
    stack: str,
    goal_hierarchy: List[str],
    decision_rules: List[tuple[str, str]],
    guardrails: List[str],
    escalation_triggers: List[str],
    output_path: str = "CLAUDE.md"
):
    """Generate a CLAUDE.md with embedded intent architecture."""

    goals_md = "\n".join(
        f"{i+1}. **{goal}**" for i, goal in enumerate(goal_hierarchy)
    )
    rules_md = "\n".join(
        f"- **{condition}**: {resolution}"
        for condition, resolution in decision_rules
    )
    guardrails_md = "\n".join(f"- ❌ {g}" for g in guardrails)
    escalation_md = "\n".join(f"- {t}" for t in escalation_triggers)

    content = f"""# CLAUDE.md — {project_name}

## Stack
{stack}

## Intent Architecture

### Goal Hierarchy (enforced, highest priority first)
{goals_md}

### Decision Rules
{rules_md}

### Hard Guardrails (never do these)
{guardrails_md}

### Escalation Triggers (stop and ask before)
{escalation_md}

## Context Notes
- This file is loaded at the start of every Claude Code session.
- The intent architecture governs ALL decisions, not just the current task.
- If you detect a conflict between a task request and this intent, surface it.
- If uncertain about intent alignment, ask rather than assume.
"""

    Path(output_path).write_text(content)
    print(f"Generated {output_path}")


# EH&S project example
generate_claude_md(
    project_name="EH&S Management System",
    stack="Python 3.12 / FastAPI / PostgreSQL / Docker",
    goal_hierarchy=[
        "Regulatory accuracy (OSHA/EPA citations are correct and current)",
        "Data integrity (all changes have audit trails)",
        "Safety (no hazard data is silently dropped or misclassified)",
        "Correctness (tests pass before merging)",
        "Performance (only after correctness is verified)"
    ],
    decision_rules=[
        ("Speed vs. Compliance", "Always choose compliance. Log the trade-off."),
        ("Scope expansion detected", "Complete stated task; add TODO for expansion."),
        ("Ambiguous regulatory logic", "Ask before assuming. Regulations are precise."),
        ("Test failure vs. deadline", "Fix the test. Never skip or suppress it."),
    ],
    guardrails=[
        "Do not remove validation from OSHA/EPA citation lookup",
        "Do not skip audit log insertion for any data modification",
        "Do not hardcode regulatory thresholds (they change; use config)",
        "Do not bypass authentication for 'dev convenience'",
        "Do not silently swallow exceptions in safety-critical paths",
    ],
    escalation_triggers=[
        "Any schema migration affecting incident or compliance records",
        "Changes to hazardous material classification logic",
        "Modifications to reporting output formats used for regulatory submission",
        "Adding or removing any mandatory field in safety forms",
        "Changes that affect more than 10 files for a 1–2 file task",
    ]
)
```

---

## Claude Code Skills & the lril-skills Repository

### How Claude Code Skills Work (2025/2026)

Claude Code Skills are markdown files with YAML frontmatter that implement **lazy-loaded context**. The key insight from the TDS research:

- **At session start**: Only the `name` and `description` fields are loaded (~100 tokens per skill)
- **On invocation**: The full skill body loads (~5,000 tokens)
- **On reference**: Additional files linked in the body load just-in-time

This makes Skills the ideal vehicle for intent engineering — they carry specialized intent context only when it's relevant to the current task.

```
CLAUDE.md (always loaded, ~500–2000 tokens)
  └── Global intent architecture + project context

Skills (lazy-loaded, ~100 tokens metadata each)
  └── intent-engine/SKILL.md ← specialized intent workflows
  └── sds-analyzer/SKILL.md  ← safety data extraction
  └── port-authority/SKILL.md ← (other skills in lril-skills)
```

### The lril-skills Repository Structure

The `seanrobertwright/lril-skills` repository contains a collection of Claude Code skills including an `intent-engine` skill under development. Based on the repository structure observed:

```
lril-skills/
├── intent-engine/     ← The skill being evaluated
├── port-authhority/   ← Port management skill
├── skills/            ← Additional skills
├── lib/               ← Shared library code
├── bin/               ← Executable scripts
├── scripts/           ← Utility scripts
└── SKILL.md           ← Root skill definition
```

---

## Evaluating & Improving the Intent-Engine Skill

### Common Gaps in Early Intent Engine Skills

Based on the research into intent engineering principles and Claude Code skill best practices, here are the most common gaps to address when building or refining an intent-engine skill:

**Gap 1 — Missing Decision Hierarchy**
Most early intent skills define *what* goals are, but not *which goal wins* when they conflict. Without a priority order, the agent will default to the easiest-to-measure metric.

**Gap 2 — No Machine-Verifiable Outcomes**
Intent specs that use language like "improve user experience" cannot be verified by an agent. Every intent needs a `verification_command` or observable metric.

**Gap 3 — No Escalation Logic**
Without explicit triggers for when to pause and ask a human, agents operating autonomously will make judgment calls that may not align with stakeholder expectations.

**Gap 4 — Intent Drift Over Long Sessions**
In multi-turn or multi-agent sessions, the intent architecture established at the start can get "compressed away" if it's not reinforced in the context. Good intent skills include compaction-resistant summaries.

**Gap 5 — Static Not Dynamic**
Intent specs that can't be updated or versioned become stale. A good intent engine should support spec versioning and change detection.

### Recommended Improvements for the intent-engine Skill

1. **Add an IntentSpec parser** — automate conversion of markdown specs into structured agent prompts
2. **Add verification hooks** — each intent spec should map to a runnable verification command
3. **Embed goal hierarchy** — not just goals, but priority ordering and conflict resolution rules
4. **Add session reinforcement** — key intent rules should survive context compaction
5. **Add an intent audit trail** — log which intents were active, what decisions were made, and against which criteria

---

## Improved SKILL.md Template

Below is a complete, production-ready SKILL.md for an intent engine skill based on all research findings. This is designed for use with Claude Code in an agentic coding environment.

```markdown
---
name: intent-engine
description: >
  Activate when working on feature specs, complex multi-file tasks, agent
  workflows, or any task where goal clarity, conflict resolution, or
  verification criteria are needed. Translates human goals into structured,
  machine-actionable intent specs that Claude Code can execute, verify, and
  audit. Use before starting any task estimated to touch more than 3 files
  or requiring cross-functional decisions.
---

# Intent Engine

## Overview

The Intent Engine bridges the gap between vague human goals and precise,
executable agent behavior. It provides:

1. **Intent Spec templates** — structured task definitions with verification
2. **Goal hierarchy enforcement** — explicit priority ordering for conflict resolution  
3. **Escalation logic** — when to pause and ask vs. proceed
4. **Session reinforcement** — intent context that survives compaction

## Core Concepts

### The Three Layers
- **Prompt**: What to do right now
- **Context**: What you know and can access  
- **Intent**: What you should optimize for over time ← this skill

### IntentSpec Format
Every significant task should have an IntentSpec. The minimum viable spec:

```yaml
# .intents/<slug>.md
intent: <slug>
priority: critical | high | medium | low
---

## IntentSpec: <Title>

### Objective
[Evidence-grounded problem statement]

### User Goal
As a [user], I need to [action] so that [outcome].

### Outcomes (Verifiable)
- [ ] [Measurable state change with method]

### Constraints
- [What must not change]

### Edge Cases
- When [condition]: [behavior]

### Conflict Resolution
[Which goal wins if they conflict]

### Verification
- `[command that proves success]`
```

## Workflow

### Step 1: Intent Capture
Before starting a task, run:
```bash
cat .claude/intent-engine/templates/spec.md
```
Fill out each section. Store in `.intents/<slug>.md`.

### Step 2: Hierarchy Check
Confirm the task aligns with the project goal hierarchy in CLAUDE.md:
- Does this task serve the top-priority goals?
- Does it conflict with any guardrail?
- Does it require human approval per escalation rules?

### Step 3: Execution with Intent Anchoring
Include the intent spec summary in every agent invocation for multi-step tasks:
```
ACTIVE INTENT: <title> (priority: <level>)
Goal: <user goal>
Success criteria: <key outcomes>
Stop if: <escalation triggers>
```

### Step 4: Verification
On task completion, verify against each outcome:
```bash
# Run the verification command from the intent spec
<verification_command>
```

### Step 5: Intent Audit
Log the result to `.intents/audit.log`:
```
[timestamp] intent=<slug> priority=<level> score=<0-1> passed=<true/false>
```

## Decision Framework

### When to Escalate (Stop and Ask)
- Detected conflict between task scope and active intent
- Task touches security, auth, or compliance logic
- File change count exceeds estimate by 3x or more
- Ambiguous regulatory or safety requirement
- Destructive operation (delete, overwrite, migration)

### Goal Priority Reference
(Override with project-specific hierarchy in CLAUDE.md)
1. Safety & compliance
2. Data integrity  
3. Correctness (tests pass)
4. Performance
5. Developer experience

### Conflict Resolution Defaults
- Safety vs. Speed → Safety wins. Always.
- Completeness vs. Scope → Complete stated task, propose expansion separately.
- Clarity vs. Cleverness → Clarity wins.

## Integration with Context Engineering

### CLAUDE.md (Intent Anchor)
The CLAUDE.md file should contain the project-level intent architecture.
This skill loads the task-level intent on top of that global foundation.

### Context Compaction Survival
During long sessions, the following must survive compaction:
1. Active intent slug and priority level
2. Hard guardrails (what is forbidden)
3. Escalation triggers currently active
4. Verification criteria for in-progress tasks

If context was compacted, begin the session with:
```
Restore intent context: what is the active intent spec and priority level?
```

## Templates

### Minimal Intent Spec
```markdown
# IntentSpec: <Title>
**Objective:** [1 sentence, evidence-grounded]
**Success:** [1 verifiable outcome]  
**Constraint:** [1 must-not-break]
**Verify:** `[command]`
```

### Full Intent Spec
See `.claude/intent-engine/templates/full-spec.md`

## Examples

### EH&S Safety Task
```markdown
# IntentSpec: OSHA 300 Log Export Fix

**Objective:** Compliance officers can't export OSHA 300 logs for Q1 2026
(bug report #247, affects annual regulatory submission due March 31).

**User Goal:** As a safety manager, I need to export a correctly formatted
OSHA 300 log so I can submit it to OSHA on time.

**Outcomes:**
- [ ] Export generates valid CSV matching OSHA 300 column spec
- [ ] All 47 incident records from Q1 appear in output
- [ ] Export completes in < 5 seconds for 500 records

**Constraints:** Must not alter existing incident records; audit log required.

**Escalation:** Stop if regulatory field mapping is ambiguous.

**Verification:** `pytest tests/exports/test_osha300.py -v`
```

### Software Feature Task
```markdown
# IntentSpec: User Dashboard Performance

**Objective:** Dashboard p95 load > 4s (observed in Datadog, 3 user complaints).

**User Goal:** As an operator, I need the dashboard to load quickly so I
can monitor facility status without delays.

**Outcomes:**
- [ ] p95 load time < 1.5s (measured via Lighthouse CI)
- [ ] No regression in data accuracy (all existing tests pass)
- [ ] Mobile layout unchanged (visual regression test passes)

**Constraints:** No changes to data model; no new external API calls.

**Conflict Resolution:** If caching vs. accuracy conflict → accuracy wins.

**Verification:** `npm run test && npm run lighthouse`
```
```

---

## Key Takeaways

### For Your Daily Coding Workflow

| Instead of... | Do this... |
|--------------|-----------|
| Write a vague ticket | Write an IntentSpec with verifiable outcomes |
| Trust the agent's judgment | Encode a goal hierarchy and conflict rules |
| Prompt once and review | Embed intent in CLAUDE.md and reinforce across sessions |
| "Fix this bug" | "Fix this bug; priority is correctness > speed; stop if auth logic involved" |
| Hope the agent doesn't drift | Build a verification step into every intent |

### For the lril-skills intent-engine Skill

1. **Add the IntentSpec frontmatter format** to the SKILL.md so Claude Code knows exactly how to structure intent files
2. **Include a goal hierarchy template** that teams can customize for their project
3. **Add escalation logic** — explicit triggers for when the agent must stop
4. **Build in verification** — each intent spec should have a runnable check
5. **Make it compaction-aware** — specify which intent elements must survive context compression
6. **Version your intents** — as the project evolves, so should the intent architecture

### The Big Shift

Prompt engineering helps you talk to AI. Context engineering helps AI understand your world. Intent engineering gets AI to **do the right thing over time** — especially when you're not watching.

For a safety professional managing a 120-person manufacturing facility, that last part isn't optional. The stakes of AI drift in an EH&S system are real: missed regulatory citations, incomplete incident records, and audit failures. Intent engineering is the discipline that makes AI agents in high-stakes domains trustworthy.

---

## Further Reading

- [Anthropic: Effective Context Engineering for AI Agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Faisal Feroz: Intent Engineering is the Real Game (Medium)](https://fferoz.medium.com/prompt-engineering-is-dead-intent-engineering-is-the-real-game-89ed83cdf3a4)
- [Martin Fowler: Context Engineering for Coding Agents](https://martinfowler.com/articles/exploring-gen-ai/context-engineering-coding-agents.html)
- [DZone: Autonomous Prompting and the Future of Intent Engineering](https://dzone.com/articles/we-taught-ai-to-talk-now-its-learning-to-talk-to-it)
- [Pathmode: Intent Engineering Glossary](https://pathmode.io/glossary/intent-engineering)
- [Towards Data Science: Claude Skills and Subagents](https://towardsdatascience.com/claude-skills-and-subagents-escaping-the-prompt-engineering-hamster-wheel/)
- [arXiv: Context Engineering for Multi-Agent LLM Code Assistants](https://arxiv.org/html/2508.08322v1)

---

*Document generated March 5, 2026 | Research synthesized from 15+ sources across industry publications, academic papers, and engineering blogs*
