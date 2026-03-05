"""
Run an Intent Engine cycle: compile -> plan -> verify.

Usage:
    python run_intent_engine.py <spec.md>           # full cycle from spec file
    echo "Fix my port conflicts" | python run_intent_engine.py --stdin  # from text
    python run_intent_engine.py <spec.md> --run-checks  # also run verification commands
    python run_intent_engine.py <spec.md> --audit       # full cycle + audit log
"""

import json
import sys
import uuid
from pathlib import Path

# Add scripts dir to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from intent_compile import parse_spec_file, compile_from_stdin, parse_spec_content
from intent_validate import (
    load_schema,
    validate_required_fields,
    validate_goal_hierarchy_compliance,
    run_verification_commands,
    compute_score,
    append_audit_log,
)


def build_plan(intent: dict) -> dict:
    """Build a plan skeleton from the intent. In production, wire to real tools."""
    plan = {
        "id": f"plan-{uuid.uuid4().hex[:8]}",
        "intent_id": intent["id"],
        "steps": [],
        "rationale": None
    }

    # Auto-generate verification steps from verification_commands
    for i, cmd_spec in enumerate(intent.get("verification_commands", []), 1):
        plan["steps"].append({
            "id": f"verify-{i}",
            "tool": "shell",
            "action": "run_verification",
            "args": {"command": cmd_spec["command"]},
            "depends_on": [],
            "can_fail": not cmd_spec.get("required", True)
        })

    if not plan["steps"]:
        plan["rationale"] = "No verification commands defined; plan requires manual step creation."

    return plan


def build_verification(intent: dict, plan: dict, run_checks: bool = False) -> dict:
    """Build verification report."""
    verification = {
        "decision": "accept",
        "score": 0.0,
        "failed_checks": [],
        "required_clarifications": [],
        "notes": [],
        "verification_results": [],
        "goal_hierarchy_respected": True
    }

    # Check personal intent confidence
    confidence = intent.get("personal_intent", {}).get("confidence", 1.0)
    if confidence < 0.6:
        verification["decision"] = "clarify"
        verification["required_clarifications"] = [
            "Are we optimizing for shipping fast, learning deeply, or reducing risk?",
            "What would make this a win today?"
        ]
        verification["notes"].append("Personal intent confidence below threshold (0.6)")

    # Check escalation triggers for high/critical risk
    risk_tier = intent.get("risk_tier", "low")
    if risk_tier in ("high", "critical") and intent.get("require_human_review"):
        if verification["decision"] == "accept":
            verification["decision"] = "escalate"
        verification["notes"].append(f"Risk tier '{risk_tier}' requires human review")

    # Run verification commands if requested
    if run_checks:
        results = run_verification_commands({"intent": intent})
        verification["verification_results"] = results
        verification["score"] = compute_score(results)

        failed = [r["command"] for r in results if not r["passed"]]
        verification["failed_checks"] = failed

        if verification["score"] < 0.8 and verification["decision"] == "accept":
            verification["decision"] = "revise"
            verification["notes"].append(f"Score {verification['score']} below 0.8 threshold")
    else:
        verification["notes"].append("Verification commands not executed (use --run-checks)")

    # Check goal hierarchy
    warnings = validate_goal_hierarchy_compliance({"intent": intent})
    if warnings:
        verification["goal_hierarchy_respected"] = False
        verification["notes"].extend(warnings)

    return verification


def build_compaction_anchor(intent: dict) -> str:
    """Generate compaction-resistant summary block."""
    hierarchy = intent.get("goal_hierarchy", [])
    hierarchy_str = " ".join(f"{g['rank']}.{g['goal']}" for g in hierarchy[:3])
    modes = intent.get("personal_intent", {}).get("modes", ["ship"])
    triggers = intent.get("escalation_triggers", [])
    trigger_str = ", ".join(t["condition"][:40] for t in triggers[:3]) or "none defined"
    commands = intent.get("verification_commands", [])
    verify_str = commands[0]["command"] if commands else "none defined"

    return (
        f"--- INTENT ANCHOR (survive compaction) ---\n"
        f"ACTIVE INTENT: {intent.get('objective', 'unknown')[:60]} "
        f"(v{intent.get('version', '1.0.0')}, priority: {intent.get('risk_tier', 'medium')})\n"
        f"GOAL HIERARCHY: {hierarchy_str}\n"
        f"MODE: {', '.join(modes)}\n"
        f"ESCALATE IF: {trigger_str}\n"
        f"VERIFY: {verify_str}\n"
        f"--- END INTENT ANCHOR ---"
    )


def run_engine(intent: dict, run_checks: bool = False) -> dict:
    """Run the full intent engine cycle."""
    plan = build_plan(intent)
    verification = build_verification(intent, plan, run_checks)
    anchor = build_compaction_anchor(intent)

    return {
        "intent": intent,
        "plan": plan,
        "verification": verification,
        "summary": anchor
    }


def main():
    run_checks = "--run-checks" in sys.argv
    do_audit = "--audit" in sys.argv

    # Parse intent from source
    if "--stdin" in sys.argv:
        intent = compile_from_stdin()
    elif len(sys.argv) >= 2 and not sys.argv[1].startswith("-"):
        intent = parse_spec_file(sys.argv[1])
    else:
        print("Usage: python run_intent_engine.py <spec.md> [--run-checks] [--audit]", file=sys.stderr)
        print("       echo 'text' | python run_intent_engine.py --stdin", file=sys.stderr)
        sys.exit(1)

    # Run engine cycle
    result = run_engine(intent, run_checks)

    # Audit log
    if do_audit:
        score = result["verification"]["score"]
        decision = result["verification"]["decision"]
        hierarchy_ok = result["verification"]["goal_hierarchy_respected"]
        append_audit_log(result, score, decision, hierarchy_ok)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
