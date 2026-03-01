# Port Authhority — Design Document

## Overview

A Claude Code skill that helps developers manage Docker port conflicts during local development. It proactively detects port conflicts before deploying containers and reactively diagnoses issues when containers fail to start or misbehave.

## Requirements

- **Detect** port conflicts before deploying (proactive)
- **Diagnose** existing conflicts when things go wrong (reactive)
- **Auto-trigger** when Docker/compose context appears in conversation
- **Cover** `docker run`, `docker compose`, and Docker Desktop workflows
- **Check** both Docker containers AND host processes for port usage
- **Support** Windows, WSL, macOS, and Linux
- **Use** a bundled Python script for data collection (Docker SDK + PyYAML)
- **Suggest + auto-fix** with conservative confirmation before any changes

## Skill Structure

```
port-authhority/
├── SKILL.md              # Skill instructions for Claude
├── scripts/
│   └── port_scanner.py   # Core data-gathering + conflict analysis
└── references/
    └── common-ports.md   # Well-known port reference
```

### Trigger

The SKILL.md description includes keywords: `docker`, `container`, `port`, `port conflict`, `docker compose`, `docker-compose`, `deploy`, `port mapping`, `port binding`, `address already in use`.

### Allowed Tools

Pre-approved: `Bash` (run script + Docker commands), `Edit` (compose file modifications).

## Python Script Design (`port_scanner.py`)

Single script with four main functions, outputting structured JSON.

### Data Gathering

1. **`get_docker_containers()`** — Docker SDK to list all containers (running + stopped). Captures: container ID, name, image, state, port mappings (host port, container port, protocol, bind address).

2. **`get_compose_ports(path)`** — PyYAML to parse `docker-compose.yml`/`compose.yml`. Extracts declared port mappings per service, including services not yet running.

3. **`get_host_ports()`** — Cross-platform host port detection:
   - Linux: `ss -tlnp`
   - macOS: `lsof -iTCP -sTCP:LISTEN -P -n`
   - Windows: `netstat -ano` + `tasklist` for PID-to-name mapping

### Analysis

4. **`analyze_conflicts(docker_ports, compose_ports, host_ports)`** — Cross-references all sources:
   - Active conflicts (Docker container vs host process)
   - Container-to-container conflicts (same host port)
   - Pending conflicts (compose file vs already-in-use port)
   - Suggestions (nearest available alternative port)

### Output Format

```json
{
  "platform": "windows|linux|darwin",
  "docker_desktop": true|false,
  "containers": [...],
  "compose_services": [...],
  "host_ports": [...],
  "conflicts": [
    {
      "type": "container-host|container-container|compose-pending",
      "port": 3000,
      "protocol": "tcp",
      "parties": ["container:myapp", "process:node(PID 1234)"],
      "suggestion": "Use port 3001 (available)"
    }
  ],
  "summary": { "total_ports": 12, "conflicts": 2, "containers": 5 }
}
```

### Dependencies

- `docker` (Docker SDK for Python)
- `pyyaml`
- Standard library only for OS port detection

### Graceful Degradation

- Docker not running: inform user, offer to check again
- Docker not installed: skip Docker checks, still scan host ports
- Permission denied: suggest elevated privileges
- Python not available: fall back to inline Docker CLI commands

## SKILL.md Workflow

### Phase 1: Scan

- Run `port_scanner.py`
- Parse JSON output
- Present formatted report: container table, host port table, compose services

### Phase 2: Analyze & Report

- Present each conflict with: what's conflicting, why it matters, suggested fix
- If no conflicts: confirm all clear with summary

### Phase 3: Fix (with confirmation)

- Offer specific fix actions per conflict:
  - Compose file edits (change host port mapping)
  - Container restart with different port
  - Kill conflicting host process
- Always ask before acting
- Re-run scan after fixes to verify resolution

## Edge Cases

- **Docker Desktop:** Detects VM-based networking, adjusts port visibility
- **WSL2:** Checks both WSL2 and Windows host ports for cross-context conflicts
- **Bind addresses:** `0.0.0.0` conflicts with everything; `127.0.0.1` and `192.168.1.5` don't conflict with each other
- **UDP vs TCP:** Protocol-aware conflict detection

## Common Ports Reference

The `references/common-ports.md` file maps well-known ports to services (80/443 HTTP/S, 3000 React/Express, 3306 MySQL, 5432 PostgreSQL, 5173 Vite, 6379 Redis, 8080 alt HTTP, 27017 MongoDB) so Claude provides contextual suggestions.
