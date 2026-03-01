# Intent Engine Plugin Interface (Domain Plugins)

A Domain Plugin defines how a domain:
- infers risk
- provides default constraints
- builds a plan (steps + tools)
- verifies results (validators + decision)

It is intentionally language-agnostic. Implement as Python classes, configs, or documentation-driven specs.

## Core types

### Intent (input)
- domain: string (e.g., "ports", "ehs")
- objective: string
- inputs: object (domain-specific)
- constraints: array of { name, value, hard, rationale? }
- success: array of { name, metric?, threshold?, description? }
- risk_tier: low|medium|high|critical
- ambiguity_policy: clarify|assume_conservative|best_effort
- contradiction_policy: flag_and_pause|choose_highest_authority|merge_with_notes
- require_evidence: bool
- require_human_review: bool
- output_format: string|null
- personal_intent: object (see resources/personal-intent.md)

### Plan (output)
- steps: ordered list of { id, tool, action, args, depends_on?, can_fail? }

### ExecutionResult (input to verify)
- step_results: list of { step_id, ok, output, evidence?, error? }
- artifacts: object (final outputs)
- combined_evidence: list (optional)

### VerificationReport (output)
- decision: accept|revise|clarify|escalate|refuse
- score: 0..1
- failed_checks: string[]
- required_clarifications: string[]
- notes: string[]

## Recommended shared tool names (for plans)
These are registry keys. Your runtime maps them to real implementations.

- parse_compose
- scan_host_ports
- allocate_ports
- write_compose
- write_reservations
- validate_no_collisions
- retrieve_docs
- extract_equipment_profile
- detect_contradictions
- draft_loto
- validate_loto_checklist
- format_output

## Personal intent integration (recommended)
Plugins MAY adjust planning and verification using personal intent modes:

- ship → minimize steps/diffs; time-box
- learn → include explanations and checkpoints
- stabilize → add tests/validation/observability
- refactor → include cleanup steps with risk gates
- de-risk → stricter verification thresholds; escalate sooner
- mentor/document → produce artifacts that help others

## Decision guidelines
- accept: all hard constraints satisfied, success met, evidence present (if required), no unresolved contradictions
- revise: execution ran but outputs fail checks; can auto-correct without new user info
- clarify: missing info or contradictions require user input / authoritative selection
- escalate: high/critical risk requires human review, or ambiguity is too dangerous
- refuse: disallowed or unsafe request
