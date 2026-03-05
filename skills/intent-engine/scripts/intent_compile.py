"""
IntentSpec compiler: parses markdown IntentSpec files into structured JSON
matching the intent.schema.json contract.

Usage:
    python intent_compile.py <spec.md>           # parse a single spec
    python intent_compile.py <spec.md> -o out.json  # write to file
    echo "Fix checkout bug" | python intent_compile.py --stdin  # from stdin (minimal)
"""

import json
import re
import sys
import uuid
from pathlib import Path


def extract_frontmatter(content: str) -> dict:
    """Extract YAML-like frontmatter from markdown."""
    match = re.match(r"---\s*\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return {}
    frontmatter = {}
    current_key = None
    current_list = None
    for line in match.group(1).split("\n"):
        line = line.rstrip()
        if not line:
            continue
        # List item under a key
        if re.match(r'^\s+-\s+', line) and current_key:
            item = re.sub(r'^\s+-\s+', '', line).strip().strip('"').strip("'")
            if current_list is None:
                current_list = []
            current_list.append(item)
            frontmatter[current_key] = current_list
            continue
        # Key: value
        if ":" in line:
            if current_list is not None:
                current_list = None
            k, v = line.split(":", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            current_key = k
            if v:
                frontmatter[k] = v
                current_list = None
            else:
                current_list = []
    return frontmatter


def extract_section(content: str, name: str) -> str:
    """Extract content under a ### heading."""
    pattern = rf"###\s+{re.escape(name)}\s*\n(.*?)(?=\n###|\n##\s|\Z)"
    match = re.search(pattern, content, re.DOTALL)
    return match.group(1).strip() if match else ""


def extract_list_items(section_content: str) -> list:
    """Extract bullet points and checkbox items from a section."""
    items = re.findall(r"^[-*]\s+\[.\]\s+(.+)$", section_content, re.MULTILINE)
    if not items:
        items = re.findall(r"^[-*]\s+(.+)$", section_content, re.MULTILINE)
    return items


def extract_bold_field(content: str, field: str) -> str:
    """Extract a **Field:** value pattern."""
    pattern = rf"\*\*{re.escape(field)}:\*\*\s*(.+?)(?:\n|$)"
    match = re.search(pattern, content)
    return match.group(1).strip() if match else ""


def extract_verification_commands(section_content: str) -> list:
    """Extract verification commands from backtick-wrapped commands."""
    commands = re.findall(r"`([^`]+)`", section_content)
    results = []
    for cmd in commands:
        # Skip template placeholders
        if cmd.startswith("[") or cmd.startswith("<"):
            continue
        results.append({
            "command": cmd,
            "description": f"Run: {cmd}",
            "weight": 1.0,
            "required": True
        })
    return results


def parse_goal_hierarchy(section_content: str) -> list:
    """Parse numbered goal hierarchy list."""
    items = re.findall(r"^\d+\.\s+\*\*(.+?)\*\*(?::\s*(.+))?$", section_content, re.MULTILINE)
    if not items:
        items = re.findall(r"^\d+\.\s+(.+?)(?::\s*(.+))?$", section_content, re.MULTILINE)
    hierarchy = []
    for i, (goal, desc) in enumerate(items, 1):
        entry = {"rank": i, "goal": goal.strip()}
        if desc:
            entry["description"] = desc.strip()
        hierarchy.append(entry)
    return hierarchy


def parse_escalation_triggers(section_content: str) -> list:
    """Parse escalation trigger bullet points."""
    items = extract_list_items(section_content)
    return [{"condition": item, "action": "pause"} for item in items]


def parse_conflict_resolution(section_content: str) -> list:
    """Parse conflict resolution rules."""
    lines = [l.strip() for l in section_content.split("\n") if l.strip()]
    results = []
    for line in lines:
        line = re.sub(r'^[-*]\s+', '', line)
        # Match "If X vs Y: Z" or "X vs Y -> Z" patterns
        match = re.match(r"(?:If\s+)?(.+?)\s*(?::|->|=>)\s*(.+)", line)
        if match:
            results.append({
                "condition": match.group(1).strip(),
                "resolution": match.group(2).strip()
            })
    return results


def parse_constraints(section_content: str) -> list:
    """Parse constraints into structured objects."""
    items = extract_list_items(section_content)
    constraints = []
    for item in items:
        constraints.append({
            "name": item[:80],
            "value": item,
            "hard": True,
            "rationale": ""
        })
    return constraints


def parse_spec_file(filepath: str) -> dict:
    """Parse a markdown IntentSpec file into a structured intent dict."""
    content = Path(filepath).read_text(encoding="utf-8")
    return parse_spec_content(content)


def parse_spec_content(content: str) -> dict:
    """Parse IntentSpec markdown content into a structured intent dict."""
    frontmatter = extract_frontmatter(content)

    # Extract title
    title_match = re.search(r"#\s+IntentSpec:\s*(.+)", content)
    title = title_match.group(1).strip() if title_match else "Untitled"

    # Extract sections
    objective = extract_section(content, "Objective") or extract_bold_field(content, "Objective")
    user_goal = extract_section(content, "User Goal") or extract_bold_field(content, "User Goal")
    outcomes_content = extract_section(content, "Outcomes")
    constraints_content = extract_section(content, "Constraints") or extract_bold_field(content, "Constraint")
    edge_cases_content = extract_section(content, "Edge Cases")
    conflict_content = extract_section(content, "Conflict Resolution") or extract_bold_field(content, "Conflict Resolution")
    hierarchy_content = extract_section(content, "Goal Hierarchy")
    escalation_content = extract_section(content, "Escalation Triggers") or extract_bold_field(content, "Escalation")
    verification_content = extract_section(content, "Verification") or extract_bold_field(content, "Verify")

    # Parse success criteria from outcomes
    outcomes = extract_list_items(outcomes_content) if outcomes_content else []
    success = [{"name": o[:80], "description": o} for o in outcomes]

    # Parse bold-field shortcuts (minimal spec format)
    success_field = extract_bold_field(content, "Success")
    if success_field and not success:
        success = [{"name": success_field[:80], "description": success_field}]

    # Parse goal hierarchy
    goal_hierarchy = parse_goal_hierarchy(hierarchy_content) if hierarchy_content else [
        {"rank": 1, "goal": "Safety & compliance"},
        {"rank": 2, "goal": "Data integrity"},
        {"rank": 3, "goal": "Correctness"},
        {"rank": 4, "goal": "Performance"},
        {"rank": 5, "goal": "Developer experience"}
    ]

    # Parse escalation triggers
    escalation_triggers = parse_escalation_triggers(escalation_content) if escalation_content else []

    # Parse verification commands
    verification_commands = extract_verification_commands(verification_content) if verification_content else []

    # Parse constraints
    constraints = parse_constraints(constraints_content) if constraints_content else []

    # Parse conflict resolution
    conflict_resolution = parse_conflict_resolution(conflict_content) if conflict_content else []

    # Determine risk tier from priority
    priority = frontmatter.get("priority", "medium")
    risk_map = {"critical": "critical", "high": "high", "medium": "medium", "low": "low"}
    risk_tier = risk_map.get(priority, "medium")

    intent = {
        "id": frontmatter.get("intent", str(uuid.uuid4())),
        "version": frontmatter.get("version", "1.0.0"),
        "domain": frontmatter.get("domain", "general"),
        "objective": objective or title,
        "inputs": {},
        "constraints": constraints,
        "success": success,
        "risk_tier": risk_tier,
        "goal_hierarchy": goal_hierarchy,
        "escalation_triggers": escalation_triggers,
        "verification_commands": verification_commands,
        "conflict_resolution": conflict_resolution,
        "changelog": frontmatter.get("changelog", [f"{frontmatter.get('version', '1.0.0')}: Initial spec"]),
        "ambiguity_policy": "clarify",
        "contradiction_policy": "flag_and_pause",
        "require_evidence": risk_tier in ("high", "critical"),
        "require_human_review": risk_tier == "critical",
        "output_format": None,
        "personal_intent": {
            "modes": ["ship"],
            "values": [],
            "tradeoffs": [],
            "anti_goals": [],
            "definition_of_done": [o for o in outcomes] if outcomes else ["working result"],
            "energy_budget": "medium",
            "time_horizon": "today",
            "confidence": 0.4
        }
    }

    return intent


def compile_from_stdin() -> dict:
    """Create a minimal intent from freeform stdin text."""
    text = sys.stdin.read().strip()
    return {
        "id": str(uuid.uuid4()),
        "version": "1.0.0",
        "domain": "unknown",
        "objective": text[:200],
        "inputs": {},
        "constraints": [],
        "success": [],
        "risk_tier": "low",
        "goal_hierarchy": [
            {"rank": 1, "goal": "Safety & compliance"},
            {"rank": 2, "goal": "Correctness"},
            {"rank": 3, "goal": "Performance"}
        ],
        "escalation_triggers": [],
        "verification_commands": [],
        "conflict_resolution": [],
        "changelog": ["1.0.0: Auto-generated from freeform text"],
        "ambiguity_policy": "clarify",
        "contradiction_policy": "flag_and_pause",
        "require_evidence": False,
        "require_human_review": False,
        "output_format": None,
        "personal_intent": {
            "modes": ["ship"],
            "values": [],
            "tradeoffs": [{"axis": "speed vs correctness", "preference": "speed", "notes": "default"}],
            "anti_goals": ["no rewrites unless requested"],
            "definition_of_done": ["working result"],
            "energy_budget": "medium",
            "time_horizon": "today",
            "confidence": 0.4
        }
    }


def main():
    if "--stdin" in sys.argv:
        intent = compile_from_stdin()
    elif len(sys.argv) >= 2 and sys.argv[1] != "-o":
        filepath = sys.argv[1]
        intent = parse_spec_file(filepath)
    else:
        print("Usage: python intent_compile.py <spec.md> [-o output.json]", file=sys.stderr)
        print("       echo 'text' | python intent_compile.py --stdin", file=sys.stderr)
        sys.exit(1)

    output = json.dumps(intent, indent=2)

    if "-o" in sys.argv:
        idx = sys.argv.index("-o")
        if idx + 1 < len(sys.argv):
            Path(sys.argv[idx + 1]).write_text(output, encoding="utf-8")
            print(f"Written to {sys.argv[idx + 1]}", file=sys.stderr)
            return

    print(output)


if __name__ == "__main__":
    main()
