---
domain: ehs
version: 0.1
risk_default: high
---

# EH&S Plugin (Intent Engine)

## What this plugin does
Produces draft safety artifacts (initially LOTO) with strict safety guardrails:
- never invents equipment isolation points or hazards
- flags contradictions across sources
- requires evidence when asked
- escalates to human review for high-risk outputs

## Domain inputs (suggested)
- equipment_id: string (e.g., "Press #7")
- site: string|null
- doc_sources: array (paths/links/repo ids)
- company_policy_refs: array
- regulatory_scope: array (e.g., ["OSHA 29 CFR 1910.147"])
- output_type: "loto" | "sop" | "inspection_checklist"
- output_format: "markdown" | "docx" | "pdf"
- required_sections: array|null

## Default constraints (LOTO)
Hard:
- do_not_fabricate_isolation_points = true
- require_shutdown_isolation_verification_steps = true
- align_with_regulatory_scope = true
- contradictions_handling = per intent.contradiction_policy

Soft:
- match_company_style = true
- include_training_notes = true

## Planning template (LOTO)
1) retrieve_docs (site policy, equipment manual, prior LOTO, EHS procedures)
2) extract_equipment_profile (energy sources, stored energy, isolation points, hazards)
3) detect_contradictions (between sources; list them)
4) draft_loto (draft only with known facts; mark unknowns explicitly)
5) validate_loto_checklist (OSHA + internal checklist)
6) format_output (markdown/docx)

## Validators (LOTO checklist)

### Required (must pass)
- R1: Equipment identification present (id, location/site if available)
- R2: All energy sources enumerated OR explicitly marked “UNKNOWN — requires confirmation”
- R3: Isolation points listed OR marked UNKNOWN (no guessing)
- R4: Stored energy controls addressed (bleed, block, discharge) OR marked UNKNOWN
- R5: Step order includes shutdown → isolation → lock/tag → verification → return to service
- R6: PPE / hazards addressed OR marked UNKNOWN
- R7: If contradictions found and contradiction_policy=flag_and_pause → decision=clarify or escalate (not accept)
- R8: If require_evidence=true → every key claim has an evidence pointer (doc ref / trace)

### Escalation gates
- E1: risk_tier high/critical → require_human_review=true
- E2: Any “UNKNOWN” fields in energy isolation or stored energy → decision=clarify
- E3: Conflicting isolation steps across sources → decision=clarify or escalate

## Clarification prompts (standard)
- List all energy sources (electrical, pneumatic, hydraulic, gravity, thermal, chemical).
- Provide physical isolation points (disconnects, valves, breakers) and locations/labels.
- Describe stored energy hazards and bleed-down/discharge methods.
- Confirm verification method (try-start/test) and responsible roles.

## Risk inference
- high by default for LOTO/SOP generation
- critical if user requests bypassing safety steps or wants “sign-off ready” without review

## Goal Hierarchy Overrides

When the EH&S domain plugin is active, the default goal hierarchy is overridden:

1. **Regulatory accuracy** -- OSHA/EPA citations are correct and current
2. **Data integrity** -- all changes have audit trails; never silently drop safety data
3. **Safety** -- no hazard data is fabricated, misclassified, or silently dropped
4. **Correctness** -- tests pass; LOTO step order is valid
5. **Performance** -- only after correctness and compliance are verified

### Domain-Specific Conflict Resolution
- **Speed vs. Compliance**: Compliance wins. Always. Log the trade-off.
- **Completeness vs. Regulatory scope**: Complete the regulatory requirement; propose expansion separately.
- **Ambiguous regulatory logic**: Ask before assuming. Regulations are precise.
- **Template convenience vs. Accuracy**: Accuracy wins. Never auto-fill safety-critical fields.

## Verification Commands

Domain-specific verification commands for EH&S intents:

- `pytest tests/compliance/ -v --tb=short` -- Run compliance test suite
- `pytest tests/exports/ -v` -- Validate export formats (OSHA 300, incident logs)
- `python -m mypy --strict src/ehs/` -- Type-check safety-critical modules
- `python scripts/validate_citations.py` -- Verify OSHA/EPA citation references

These are suggested defaults. Individual IntentSpecs should override with
task-specific commands in their `### Verification` section.

## Personal intent mapping
- ship:
  - draft quickly, but do not bypass unknowns/safety gates
  - likely clarify/escalate if isolation info is missing
- learn:
  - include brief “why this step exists” notes for OSHA-required items
- stabilize / de-risk:
  - stricter verification; require evidence by default
  - escalate to human review more often
