"""
Intent compiler placeholder.
Given freeform text, produce a normalized intent dict matching the schema.

In real use: wire this to your app/agent runtime, not Claude itself.
"""

import json
import sys
import uuid

def main():
    text = sys.stdin.read().strip()
    intent = {
        "id": str(uuid.uuid4()),
        "domain": "unknown",
        "objective": text[:200],
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
            "values": [],
            "tradeoffs": [{"axis": "speed vs correctness", "preference": "speed", "notes": "default"}],
            "anti_goals": ["no rewrites unless requested"],
            "definition_of_done": ["working result"],
            "energy_budget": "medium",
            "time_horizon": "today",
            "confidence": 0.4
        }
    }
    print(json.dumps(intent, indent=2))

if __name__ == "__main__":
    main()
