"""
Intent verifier: validates intent contract JSON against the schema and
runs verification commands to check if outcomes have been achieved.

Usage:
    python intent_validate.py <intent.json>              # validate schema only
    python intent_validate.py <intent.json> --run-checks # also run verification commands
    python intent_validate.py <intent.json> --audit      # validate, run checks, and append to audit log
"""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def load_schema() -> dict:
    """Load the intent schema from the resources directory."""
    schema_path = Path(__file__).parent.parent / "resources" / "intent.schema.json"
    return json.loads(schema_path.read_text(encoding="utf-8"))


def validate_required_fields(intent: dict, schema: dict) -> list:
    """Check required fields are present (lightweight, no jsonschema dependency)."""
    errors = []

    # Check top-level required
    for field in schema.get("required", []):
        if field not in intent:
            errors.append(f"Missing required top-level field: {field}")

    # Check intent object required fields
    intent_schema = schema.get("properties", {}).get("intent", {})
    intent_obj = intent.get("intent", {})
    for field in intent_schema.get("required", []):
        if field not in intent_obj:
            errors.append(f"Missing required intent field: intent.{field}")

    # Check plan required fields
    plan_schema = schema.get("properties", {}).get("plan", {})
    plan_obj = intent.get("plan", {})
    for field in plan_schema.get("required", []):
        if field not in plan_obj:
            errors.append(f"Missing required plan field: plan.{field}")

    # Check verification required fields
    verif_schema = schema.get("properties", {}).get("verification", {})
    verif_obj = intent.get("verification", {})
    for field in verif_schema.get("required", []):
        if field not in verif_obj:
            errors.append(f"Missing required verification field: verification.{field}")

    # Check enum values
    risk_tier = intent_obj.get("risk_tier")
    if risk_tier and risk_tier not in ["low", "medium", "high", "critical"]:
        errors.append(f"Invalid risk_tier: {risk_tier}")

    decision = verif_obj.get("decision")
    if decision and decision not in ["accept", "revise", "clarify", "escalate", "refuse"]:
        errors.append(f"Invalid verification decision: {decision}")

    # Check goal hierarchy is non-empty
    hierarchy = intent_obj.get("goal_hierarchy", [])
    if not hierarchy:
        errors.append("goal_hierarchy must have at least 1 entry")

    # Check version is present
    if not intent_obj.get("version"):
        errors.append("intent.version is required")

    return errors


def validate_goal_hierarchy_compliance(intent: dict) -> list:
    """Check that the plan doesn't violate goal hierarchy ordering."""
    warnings = []
    hierarchy = intent.get("intent", {}).get("goal_hierarchy", [])
    if len(hierarchy) < 2:
        return warnings

    # Check that conflict resolution rules reference goals in the hierarchy
    conflict_rules = intent.get("intent", {}).get("conflict_resolution", [])
    goal_names = {g["goal"].lower() for g in hierarchy}
    for rule in conflict_rules:
        condition = rule.get("condition", "").lower()
        # Warn if a conflict rule references goals not in the hierarchy
        found_match = any(g in condition for g in goal_names)
        if not found_match and condition:
            warnings.append(f"Conflict rule '{rule['condition']}' may reference goals not in hierarchy")

    return warnings


def run_verification_commands(intent: dict) -> list:
    """Run verification commands and return results."""
    commands = intent.get("intent", {}).get("verification_commands", [])
    results = []

    for cmd_spec in commands:
        command = cmd_spec.get("command", "")
        if not command:
            continue

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=120
            )
            passed = result.returncode == 0
            output = result.stdout[:500] if passed else result.stderr[:500]
        except subprocess.TimeoutExpired:
            passed = False
            output = "Command timed out after 120 seconds"
        except Exception as e:
            passed = False
            output = str(e)

        results.append({
            "command": command,
            "passed": passed,
            "output": output,
            "weight": cmd_spec.get("weight", 1.0)
        })

    return results


def compute_score(verification_results: list) -> float:
    """Compute weighted verification score from command results."""
    if not verification_results:
        return 0.0

    total_weight = sum(r.get("weight", 1.0) for r in verification_results)
    if total_weight == 0:
        return 0.0

    weighted_passed = sum(
        r.get("weight", 1.0) for r in verification_results if r.get("passed")
    )
    return round(weighted_passed / total_weight, 3)


def append_audit_log(intent: dict, score: float, decision: str, hierarchy_ok: bool):
    """Append an entry to the intent audit log."""
    intent_obj = intent.get("intent", {})
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    slug = intent_obj.get("id", "unknown")
    version = intent_obj.get("version", "0.0.0")
    priority = intent_obj.get("risk_tier", "unknown")

    log_line = (
        f"[{timestamp}] intent={slug} version={version} priority={priority} "
        f"decision={decision} score={score} "
        f"goal_hierarchy_respected={str(hierarchy_ok).lower()} "
        f"escalations=0\n"
    )

    # Write to .intents/audit.log relative to cwd
    log_dir = Path.cwd() / ".intents"
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / "audit.log"

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(log_line)

    print(f"Audit log appended: {log_path}", file=sys.stderr)


def main():
    if len(sys.argv) < 2:
        print("Usage: python intent_validate.py <contract.json> [--run-checks] [--audit]", file=sys.stderr)
        sys.exit(1)

    filepath = sys.argv[1]
    run_checks = "--run-checks" in sys.argv
    do_audit = "--audit" in sys.argv

    # Load contract
    contract = json.loads(Path(filepath).read_text(encoding="utf-8"))

    # Load and validate against schema
    schema = load_schema()
    errors = validate_required_fields(contract, schema)

    # Check goal hierarchy compliance
    warnings = validate_goal_hierarchy_compliance(contract)

    # Run verification commands if requested
    verification_results = []
    score = contract.get("verification", {}).get("score", 0.0)
    if run_checks:
        verification_results = run_verification_commands(contract)
        score = compute_score(verification_results)

    # Determine decision
    hierarchy_ok = len(warnings) == 0
    if errors:
        decision = "revise"
    elif run_checks and score < 0.8:
        decision = "revise"
    elif run_checks and score >= 0.8:
        decision = "accept"
    else:
        decision = contract.get("verification", {}).get("decision", "accept")

    # Build result
    result = {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "goal_hierarchy_respected": hierarchy_ok,
        "decision": decision,
        "score": score
    }

    if verification_results:
        result["verification_results"] = verification_results

    # Audit log
    if do_audit:
        append_audit_log(contract, score, decision, hierarchy_ok)

    print(json.dumps(result, indent=2))

    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
