"""
Generate a CLAUDE.md with embedded intent architecture for a project.

Usage:
    python generate_claude_md.py                          # interactive prompts
    python generate_claude_md.py -o CLAUDE.md             # specify output path
    python generate_claude_md.py --preset ehs             # use EH&S preset
    python generate_claude_md.py --preset ports           # use ports preset
    python generate_claude_md.py --from-spec .intents/my-task.md  # extract from IntentSpec
"""

import argparse
import sys
from pathlib import Path

# Add scripts dir to path for imports
sys.path.insert(0, str(Path(__file__).parent))

PRESETS = {
    "ehs": {
        "project_name": "EH&S Management System",
        "stack": "Python 3.12 / FastAPI / PostgreSQL / Docker",
        "goal_hierarchy": [
            "Regulatory accuracy (OSHA/EPA citations are correct and current)",
            "Data integrity (all changes have audit trails)",
            "Safety (no hazard data is silently dropped or misclassified)",
            "Correctness (tests pass before merging)",
            "Performance (only after correctness is verified)",
        ],
        "decision_rules": [
            ("Speed vs. Compliance", "Always choose compliance. Log the trade-off."),
            ("Scope expansion detected", "Complete stated task; add TODO for expansion."),
            ("Ambiguous regulatory logic", "Ask before assuming. Regulations are precise."),
            ("Test failure vs. deadline", "Fix the test. Never skip or suppress it."),
        ],
        "guardrails": [
            "Do not remove validation from OSHA/EPA citation lookup",
            "Do not skip audit log insertion for any data modification",
            "Do not hardcode regulatory thresholds (they change; use config)",
            "Do not bypass authentication for 'dev convenience'",
            "Do not silently swallow exceptions in safety-critical paths",
        ],
        "escalation_triggers": [
            "Any schema migration affecting incident or compliance records",
            "Changes to hazardous material classification logic",
            "Modifications to reporting output formats used for regulatory submission",
            "Adding or removing any mandatory field in safety forms",
            "Changes that affect more than 10 files for a 1-2 file task",
        ],
    },
    "ports": {
        "project_name": "Port Management System",
        "stack": "Docker Compose / Node.js / Python",
        "goal_hierarchy": [
            "No port collisions (zero conflicts in running stack)",
            "Deterministic allocation (same inputs produce same outputs)",
            "Backward compatibility (preserve existing port mappings)",
            "Correctness (validation passes on every change)",
            "Developer experience (clear mappings, easy onboarding)",
        ],
        "decision_rules": [
            ("Collision vs. Preservation", "Resolve collision; log which mapping changed."),
            ("Scope expansion detected", "Complete stated task; add TODO for expansion."),
            ("Category range conflict", "Ask before reassigning across categories."),
            ("Config drift detected", "Reconcile reservations file with compose."),
        ],
        "guardrails": [
            "Do not allow duplicate host port bindings",
            "Do not use random port allocation in production configs",
            "Do not modify ports outside the declared category ranges",
            "Do not delete the reservations file without backup",
        ],
        "escalation_triggers": [
            "Port change affects a running production service",
            "Category ranges need to be expanded or reorganized",
            "More than 5 services need port reassignment at once",
            "Reservations file conflicts with docker-compose state",
        ],
    },
}

DEFAULT_HIERARCHY = [
    "Safety & compliance",
    "Data integrity",
    "Correctness (tests pass)",
    "Performance",
    "Developer experience",
]

DEFAULT_RULES = [
    ("Safety vs. Speed", "Safety wins. Always."),
    ("Completeness vs. Scope", "Complete stated task, propose expansion separately."),
    ("Clarity vs. Cleverness", "Clarity wins."),
]

DEFAULT_GUARDRAILS = [
    "Do not bypass authentication or authorization checks",
    "Do not suppress or swallow errors silently",
    "Do not skip tests to meet deadlines",
]

DEFAULT_TRIGGERS = [
    "Task touches security, auth, or compliance logic",
    "File change count exceeds estimate by 3x",
    "Destructive operation (delete, overwrite, schema migration)",
]


def generate_claude_md(
    project_name: str,
    stack: str,
    goal_hierarchy: list[str],
    decision_rules: list[tuple[str, str]],
    guardrails: list[str],
    escalation_triggers: list[str],
) -> str:
    """Generate CLAUDE.md content with embedded intent architecture."""
    goals_md = "\n".join(
        f"{i+1}. **{goal}**" for i, goal in enumerate(goal_hierarchy)
    )
    rules_md = "\n".join(
        f"- **{condition}**: {resolution}"
        for condition, resolution in decision_rules
    )
    guardrails_md = "\n".join(f"- {g}" for g in guardrails)
    escalation_md = "\n".join(f"- {t}" for t in escalation_triggers)

    return f"""# CLAUDE.md -- {project_name}

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


def from_intent_spec(spec_path: str) -> dict:
    """Extract CLAUDE.md parameters from an IntentSpec file."""
    from intent_compile import parse_spec_file

    intent = parse_spec_file(spec_path)

    hierarchy = [g["goal"] for g in intent.get("goal_hierarchy", [])]
    if not hierarchy:
        hierarchy = DEFAULT_HIERARCHY

    rules = []
    for cr in intent.get("conflict_resolution", []):
        rules.append((cr["condition"], cr["resolution"]))
    if not rules:
        rules = DEFAULT_RULES

    constraints = [c["value"] for c in intent.get("constraints", [])]
    if not constraints:
        constraints = DEFAULT_GUARDRAILS

    triggers = [t["condition"] for t in intent.get("escalation_triggers", [])]
    if not triggers:
        triggers = DEFAULT_TRIGGERS

    return {
        "project_name": intent.get("objective", "Project")[:60],
        "stack": intent.get("domain", "general"),
        "goal_hierarchy": hierarchy,
        "decision_rules": rules,
        "guardrails": constraints,
        "escalation_triggers": triggers,
    }


def interactive_prompt() -> dict:
    """Gather CLAUDE.md parameters interactively."""
    print("Generate CLAUDE.md with Intent Architecture\n")

    project_name = input("Project name: ").strip() or "My Project"
    stack = input("Tech stack (e.g., Python 3.12 / FastAPI / PostgreSQL): ").strip() or "Not specified"

    print("\nGoal hierarchy (highest priority first, one per line, blank to finish):")
    print("  Defaults: Safety, Data integrity, Correctness, Performance, DX")
    hierarchy = []
    while True:
        goal = input(f"  {len(hierarchy)+1}. ").strip()
        if not goal:
            break
        hierarchy.append(goal)
    if not hierarchy:
        hierarchy = DEFAULT_HIERARCHY

    print("\nDecision rules (format: 'condition: resolution', blank to finish):")
    rules = []
    while True:
        rule = input("  - ").strip()
        if not rule:
            break
        if ":" in rule:
            parts = rule.split(":", 1)
            rules.append((parts[0].strip(), parts[1].strip()))
    if not rules:
        rules = DEFAULT_RULES

    print("\nHard guardrails (things the agent must never do, blank to finish):")
    guardrails = []
    while True:
        g = input("  - ").strip()
        if not g:
            break
        guardrails.append(g)
    if not guardrails:
        guardrails = DEFAULT_GUARDRAILS

    print("\nEscalation triggers (when to stop and ask, blank to finish):")
    triggers = []
    while True:
        t = input("  - ").strip()
        if not t:
            break
        triggers.append(t)
    if not triggers:
        triggers = DEFAULT_TRIGGERS

    return {
        "project_name": project_name,
        "stack": stack,
        "goal_hierarchy": hierarchy,
        "decision_rules": rules,
        "guardrails": guardrails,
        "escalation_triggers": triggers,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Generate a CLAUDE.md with embedded intent architecture"
    )
    parser.add_argument(
        "-o", "--output", default="CLAUDE.md",
        help="Output file path (default: CLAUDE.md)"
    )
    parser.add_argument(
        "--preset", choices=list(PRESETS.keys()),
        help="Use a domain preset (ehs, ports)"
    )
    parser.add_argument(
        "--from-spec",
        help="Extract intent architecture from an IntentSpec markdown file"
    )
    parser.add_argument(
        "--stdout", action="store_true",
        help="Print to stdout instead of writing a file"
    )
    args = parser.parse_args()

    if args.preset:
        params = PRESETS[args.preset]
    elif args.from_spec:
        params = from_intent_spec(args.from_spec)
    else:
        params = interactive_prompt()

    content = generate_claude_md(**params)

    if args.stdout:
        print(content)
    else:
        Path(args.output).write_text(content, encoding="utf-8")
        print(f"Generated {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
