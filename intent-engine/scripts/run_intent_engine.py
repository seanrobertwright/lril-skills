"""
Run an Intent Engine cycle locally (demo).

This is a *skeleton* that prints contract-shaped output.
Wire to real tools/validators in your runtime later.
"""

import json
import sys
import uuid

def run_engine(text: str):
    # Very lightweight demo: treat personal intent confidence as low to trigger clarify.
    intent = {
        "id": str(uuid.uuid4()),
        "domain": "unknown",
        "objective": text.strip(),
        "inputs": {},
        "constraints": [],
        "success": [],
        "risk_tier": "low",
        "ambiguity_policy": "clarify",
        "contradiction_policy": "flag_and_pause",
        "require_evidence": False,
        "require_human_review": False,
        "output_format": None,
        "personal_intent": {
            "modes": ["ship"],
            "values": ["simplicity", "speed"],
            "tradeoffs": [{"axis": "speed vs correctness", "preference": "speed", "notes": "demo default"}],
            "anti_goals": ["no big rewrites"],
            "definition_of_done": ["working result"],
            "energy_budget": "medium",
            "time_horizon": "today",
            "confidence": 0.5
        }
    }

    plan = {
        "id": "plan-placeholder",
        "intent_id": intent["id"],
        "steps": [],
        "rationale": "Demo plan (no steps yet)."
    }

    verification = {
        "decision": "clarify" if intent["personal_intent"]["confidence"] < 0.6 else "accept",
        "score": 0.5,
        "failed_checks": [],
        "required_clarifications": [
            "Are we optimizing for shipping fast, learning deeply, or reducing risk?",
            "What would make this a win today?"
        ] if intent["personal_intent"]["confidence"] < 0.6 else [],
        "notes": ["Demo runner only; wire real tools for execution/validation."]
    }

    return {"intent": intent, "plan": plan, "verification": verification}

if __name__ == "__main__":
    text = sys.stdin.read()
    print(json.dumps(run_engine(text), indent=2))
