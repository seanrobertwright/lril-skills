# Domain Catalog (Intent Engine)

## ports
Purpose: Allocate/repair port mappings for local dev stacks (Docker Compose, dev servers).
Typical risk: low/medium.
Typical tools: parse_compose, scan_host_ports, allocate_ports, write_compose, write_reservations, validate_no_collisions.
Key constraints:
- avoid collisions
- respect category ranges
- deterministic reservation mapping

## ehs
Purpose: Draft and validate safety/compliance documents (LOTO, SOPs, inspections).
Typical risk: high.
Typical tools: retrieve_docs, extract_equipment_profile, detect_contradictions, draft_loto, validate_loto_checklist, format_output.
Key constraints:
- OSHA alignment (e.g., 29 CFR 1910.147)
- company/site policy alignment
- do not fabricate missing equipment isolation points
- evidence required when requested
- contradictions handled conservatively
