## Example 1 — Ports domain (low risk)

User: "Fix my docker compose port collisions and reserve ports by category."

Personal intent (ship):
- modes: ["ship"]
- definition_of_done: ["Compose runs", "No collisions", "Reservations persisted"]

Plan steps:
1) parse_compose
2) scan_host_ports
3) allocate_ports
4) write_compose
5) write_reservations
6) validate_no_collisions

Verification:
- accept if collisions=0 and reservations match compose.

## Example 2 — EH&S domain (high risk)

User: "Draft LOTO procedure for Press #7."

Personal intent (de-risk):
- modes: ["de-risk"]
- anti_goals: ["Do not guess isolation points"]

Intent:
- domain: "ehs"
- objective: "Draft OSHA-aligned LOTO procedure for Press #7 with evidence."
- constraints: ["OSHA 1910.147", "site policy", "equipment energy sources"]
- require_evidence: true
- risk_tier: high
- ambiguity_policy: clarify
- contradiction_policy: flag_and_pause

Verification:
- If energy isolation points unknown → decision: clarify
- If sources conflict → decision: clarify/escalate (not accept)

## Example 3 — Same request, different personal intent

User: "Fix my compose port conflicts."

Case A (ship):
- plan minimizes changes; preserves existing mappings when possible.

Case B (stabilize):
- adds rerun validation, consistency checks, writes reservations, documents mapping.
