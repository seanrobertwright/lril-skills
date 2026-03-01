# Port Authhority Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Claude Code skill that detects, diagnoses, and resolves Docker port conflicts during local development.

**Architecture:** Single Python script (`port_scanner.py`) collects all port data from Docker containers, compose files, and host processes, then outputs structured JSON. SKILL.md instructs Claude through a Scan → Analyze → Fix workflow with conservative confirmation before changes.

**Tech Stack:** Python 3.8+, Docker SDK for Python (`docker`), PyYAML, platform-specific CLI tools (`ss`, `lsof`, `netstat`).

---

### Task 1: Create SKILL.md

**Files:**
- Create: `SKILL.md`

**Step 1: Write the SKILL.md file**

```markdown
---
name: port-authhority
description: >
  Manage Docker port conflicts during local development. Detects and resolves port collisions
  between Docker containers, docker compose services, and host processes.
  Use when: deploying containers, running docker compose, debugging port binding errors,
  seeing "address already in use", managing port mappings, or working with Docker Desktop.
  Keywords: docker, container, port, port conflict, docker compose, docker-compose, deploy,
  port mapping, port binding, address already in use, EADDRINUSE, bind, listen.
allowed-tools:
  - Bash
  - Edit
---

# Port Authhority

Detect, diagnose, and resolve port conflicts between Docker containers, compose services, and host processes.

## Prerequisites

This skill requires Python 3.8+ with `docker` and `pyyaml` packages. If missing, install them:

```bash
pip install docker pyyaml
```

## Workflow

### Phase 1: Scan

Run the port scanner script from the skill's `scripts/` directory:

```bash
python "<skill-directory>/scripts/port_scanner.py" [--path /optional/compose/dir]
```

The `--path` argument defaults to the current working directory. The script outputs JSON to stdout.

Parse the JSON output. Present a formatted report to the developer:

**Containers table:** Show each running container's name, image, state, and port mappings.

**Host ports table:** Show each listening host process with port, protocol, PID, and process name.

**Compose services:** If a compose file was found, show declared services and their port mappings, noting which are running and which are not.

### Phase 2: Analyze & Report

If the `conflicts` array in the JSON output is non-empty, present each conflict:

- **What:** Which port, which protocol, which parties are involved
- **Why:** Explain the impact (container won't start, traffic routed to wrong service, etc.)
- **Fix:** The suggested alternative port from the `suggestion` field

Refer to `references/common-ports.md` for context on well-known ports. For example, if port 5432 is conflicting, mention that it's typically PostgreSQL.

If no conflicts exist, confirm all clear and show the summary counts.

### Phase 3: Fix (with confirmation)

For each conflict, propose a specific fix action. **Always ask the developer before applying any change.** Possible actions:

- **Edit compose file:** Change the host port in the `ports:` mapping (e.g., `"3000:3000"` → `"3001:3000"`)
- **Restart container:** Stop the conflicting container and restart with a different host port
- **Kill host process:** Offer to kill a host process occupying the port (show PID and process name)

After applying any fix, re-run the scan to verify the conflict is resolved.

### Error Handling

- **Docker not running:** Tell the developer to start Docker. Offer to re-scan.
- **Docker not installed:** Skip Docker checks. Still scan host ports for a partial report.
- **Python not available:** Fall back to inline commands: `docker ps --format json` and `docker port <id>`.
- **Permission denied:** Suggest running with elevated privileges for full host port visibility.
- **No compose file found:** Skip compose analysis. Report only running containers and host ports.
```

**Step 2: Commit**

```bash
git add SKILL.md
git commit -m "feat: add SKILL.md with scan/analyze/fix workflow"
```

---

### Task 2: Create common ports reference

**Files:**
- Create: `references/common-ports.md`

**Step 1: Write the reference file**

```markdown
# Common Ports Reference

| Port | Service | Notes |
|------|---------|-------|
| 80 | HTTP | Web server |
| 443 | HTTPS | Secure web server |
| 1433 | MSSQL | Microsoft SQL Server |
| 3000 | Dev servers | React (CRA), Rails, Express, Grafana |
| 3306 | MySQL | MySQL / MariaDB |
| 4200 | Angular | Angular dev server |
| 5000 | Flask / Docker Registry | Python Flask dev server |
| 5173 | Vite | Vite dev server |
| 5432 | PostgreSQL | PostgreSQL database |
| 5672 | RabbitMQ | AMQP protocol |
| 6379 | Redis | Redis cache/store |
| 8000 | Django / uvicorn | Python web frameworks |
| 8080 | Alt HTTP | Tomcat, Jenkins, alternative web |
| 8443 | Alt HTTPS | Alternative secure web |
| 8888 | Jupyter | Jupyter Notebook |
| 9090 | Prometheus | Monitoring |
| 9200 | Elasticsearch | Search engine |
| 15672 | RabbitMQ Management | Web UI |
| 27017 | MongoDB | MongoDB database |
```

**Step 2: Commit**

```bash
git add references/common-ports.md
git commit -m "feat: add common ports reference file"
```

---

### Task 3: Create port_scanner.py — scaffold and platform detection

**Files:**
- Create: `scripts/port_scanner.py`
- Create: `tests/test_port_scanner.py`

**Step 1: Write the test for platform detection**

```python
# tests/test_port_scanner.py
import sys
import os
import json
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from port_scanner import detect_platform, is_docker_desktop


class TestPlatformDetection(unittest.TestCase):
    @patch('platform.system', return_value='Linux')
    def test_detect_linux(self, mock_sys):
        self.assertEqual(detect_platform(), 'linux')

    @patch('platform.system', return_value='Darwin')
    def test_detect_macos(self, mock_sys):
        self.assertEqual(detect_platform(), 'darwin')

    @patch('platform.system', return_value='Windows')
    def test_detect_windows(self, mock_sys):
        self.assertEqual(detect_platform(), 'windows')

    @patch('port_scanner.docker')
    def test_docker_desktop_detected(self, mock_docker):
        mock_client = MagicMock()
        mock_client.info.return_value = {'Name': 'docker-desktop'}
        mock_docker.from_env.return_value = mock_client
        self.assertTrue(is_docker_desktop())

    @patch('port_scanner.docker')
    def test_docker_desktop_not_detected(self, mock_docker):
        mock_client = MagicMock()
        mock_client.info.return_value = {'Name': 'my-linux-host'}
        mock_docker.from_env.return_value = mock_client
        self.assertFalse(is_docker_desktop())

    @patch('port_scanner.docker')
    def test_docker_desktop_docker_not_running(self, mock_docker):
        mock_docker.from_env.side_effect = Exception("connection refused")
        self.assertFalse(is_docker_desktop())


if __name__ == '__main__':
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `cd port-authhority && python -m pytest tests/test_port_scanner.py -v`
Expected: FAIL (module not found)

**Step 3: Write the scaffold and platform detection**

```python
#!/usr/bin/env python3
"""Port Authhority — Docker port conflict scanner.

Detects port conflicts between Docker containers, compose services,
and host processes. Outputs structured JSON for Claude to interpret.
"""

import argparse
import json
import os
import platform
import subprocess
import sys

try:
    import docker
except ImportError:
    docker = None

try:
    import yaml
except ImportError:
    yaml = None


def detect_platform() -> str:
    """Return normalized platform: 'linux', 'darwin', or 'windows'."""
    return platform.system().lower()


def is_docker_desktop() -> bool:
    """Check if Docker Desktop is running (vs native Docker Engine)."""
    if docker is None:
        return False
    try:
        client = docker.from_env()
        info = client.info()
        name = info.get('Name', '')
        return 'desktop' in name.lower()
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(description='Scan for Docker port conflicts')
    parser.add_argument('--path', default='.', help='Path to search for compose files')
    args = parser.parse_args()

    result = {
        'platform': detect_platform(),
        'docker_desktop': is_docker_desktop(),
        'containers': [],
        'compose_services': [],
        'host_ports': [],
        'conflicts': [],
        'summary': {'total_ports': 0, 'conflicts': 0, 'containers': 0},
    }

    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
```

**Step 4: Run test to verify it passes**

Run: `cd port-authhority && python -m pytest tests/test_port_scanner.py -v`
Expected: All 6 tests PASS

**Step 5: Commit**

```bash
git add scripts/port_scanner.py tests/test_port_scanner.py
git commit -m "feat: scaffold port_scanner.py with platform detection"
```

---

### Task 4: Implement get_docker_containers()

**Files:**
- Modify: `scripts/port_scanner.py`
- Modify: `tests/test_port_scanner.py`

**Step 1: Write the tests**

Add to `tests/test_port_scanner.py`:

```python
from port_scanner import get_docker_containers


class TestGetDockerContainers(unittest.TestCase):
    @patch('port_scanner.docker')
    def test_returns_container_info(self, mock_docker):
        mock_container = MagicMock()
        mock_container.short_id = 'abc123'
        mock_container.name = 'my-app'
        mock_container.image.tags = ['node:18']
        mock_container.status = 'running'
        mock_container.ports = {
            '3000/tcp': [{'HostIp': '0.0.0.0', 'HostPort': '3000'}],
            '9229/tcp': None,
        }
        mock_client = MagicMock()
        mock_client.containers.list.return_value = [mock_container]
        mock_docker.from_env.return_value = mock_client

        containers = get_docker_containers()
        self.assertEqual(len(containers), 1)
        c = containers[0]
        self.assertEqual(c['id'], 'abc123')
        self.assertEqual(c['name'], 'my-app')
        self.assertEqual(c['image'], 'node:18')
        self.assertEqual(c['state'], 'running')
        self.assertEqual(len(c['ports']), 1)  # only mapped ports
        self.assertEqual(c['ports'][0]['host_port'], 3000)
        self.assertEqual(c['ports'][0]['container_port'], 3000)
        self.assertEqual(c['ports'][0]['protocol'], 'tcp')
        self.assertEqual(c['ports'][0]['bind_address'], '0.0.0.0')

    @patch('port_scanner.docker')
    def test_no_containers(self, mock_docker):
        mock_client = MagicMock()
        mock_client.containers.list.return_value = []
        mock_docker.from_env.return_value = mock_client
        self.assertEqual(get_docker_containers(), [])

    @patch('port_scanner.docker', None)
    def test_docker_sdk_not_installed(self):
        self.assertEqual(get_docker_containers(), [])

    @patch('port_scanner.docker')
    def test_docker_not_running(self, mock_docker):
        mock_docker.from_env.side_effect = Exception("connection refused")
        self.assertEqual(get_docker_containers(), [])
```

**Step 2: Run test to verify it fails**

Run: `cd port-authhority && python -m pytest tests/test_port_scanner.py::TestGetDockerContainers -v`
Expected: FAIL (function not found)

**Step 3: Implement get_docker_containers()**

Add to `scripts/port_scanner.py` before `main()`:

```python
def get_docker_containers() -> list:
    """Get all Docker containers and their port mappings."""
    if docker is None:
        return []
    try:
        client = docker.from_env()
        containers = client.containers.list(all=True)
    except Exception:
        return []

    result = []
    for c in containers:
        ports = []
        for container_port_proto, bindings in (c.ports or {}).items():
            if bindings is None:
                continue
            port_str, protocol = container_port_proto.split('/')
            container_port = int(port_str)
            for binding in bindings:
                ports.append({
                    'host_port': int(binding['HostPort']),
                    'container_port': container_port,
                    'protocol': protocol,
                    'bind_address': binding.get('HostIp', '0.0.0.0'),
                })

        image_tags = c.image.tags if c.image.tags else [str(c.image.id[:12])]
        result.append({
            'id': c.short_id,
            'name': c.name,
            'image': image_tags[0],
            'state': c.status,
            'ports': ports,
        })
    return result
```

**Step 4: Wire into main()**

Update `main()` to call `get_docker_containers()`:

```python
    containers = get_docker_containers()
    result['containers'] = containers
    result['summary']['containers'] = len(containers)
```

**Step 5: Run test to verify it passes**

Run: `cd port-authhority && python -m pytest tests/test_port_scanner.py -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add scripts/port_scanner.py tests/test_port_scanner.py
git commit -m "feat: add get_docker_containers() with port mapping extraction"
```

---

### Task 5: Implement get_compose_ports()

**Files:**
- Modify: `scripts/port_scanner.py`
- Modify: `tests/test_port_scanner.py`

**Step 1: Write the tests**

Add to `tests/test_port_scanner.py`:

```python
import tempfile

from port_scanner import get_compose_ports


class TestGetComposePorts(unittest.TestCase):
    def _write_compose(self, content):
        """Write a compose file to a temp dir and return the dir path."""
        d = tempfile.mkdtemp()
        with open(os.path.join(d, 'docker-compose.yml'), 'w') as f:
            f.write(content)
        return d

    def test_parses_short_syntax(self):
        d = self._write_compose("""
services:
  web:
    image: nginx
    ports:
      - "8080:80"
      - "8443:443"
""")
        services = get_compose_ports(d)
        self.assertEqual(len(services), 1)
        s = services[0]
        self.assertEqual(s['service'], 'web')
        self.assertEqual(s['image'], 'nginx')
        self.assertEqual(len(s['ports']), 2)
        self.assertEqual(s['ports'][0]['host_port'], 8080)
        self.assertEqual(s['ports'][0]['container_port'], 80)

    def test_parses_long_syntax(self):
        d = self._write_compose("""
services:
  api:
    image: myapi
    ports:
      - target: 3000
        published: 3001
        protocol: tcp
""")
        services = get_compose_ports(d)
        self.assertEqual(services[0]['ports'][0]['host_port'], 3001)
        self.assertEqual(services[0]['ports'][0]['container_port'], 3000)

    def test_no_compose_file(self):
        d = tempfile.mkdtemp()
        services = get_compose_ports(d)
        self.assertEqual(services, [])

    def test_service_without_ports(self):
        d = self._write_compose("""
services:
  db:
    image: postgres
""")
        services = get_compose_ports(d)
        self.assertEqual(len(services), 1)
        self.assertEqual(services[0]['ports'], [])

    @patch('port_scanner.yaml', None)
    def test_yaml_not_installed(self):
        d = tempfile.mkdtemp()
        self.assertEqual(get_compose_ports(d), [])

    def test_host_only_port(self):
        """Port like '3000' (no host mapping) should still be captured."""
        d = self._write_compose("""
services:
  app:
    image: myapp
    ports:
      - "3000"
""")
        services = get_compose_ports(d)
        self.assertEqual(len(services[0]['ports']), 1)
        p = services[0]['ports'][0]
        self.assertEqual(p['container_port'], 3000)
        # host_port is dynamic/random when not specified
        self.assertIsNone(p['host_port'])
```

**Step 2: Run test to verify it fails**

Run: `cd port-authhority && python -m pytest tests/test_port_scanner.py::TestGetComposePorts -v`
Expected: FAIL

**Step 3: Implement get_compose_ports()**

Add to `scripts/port_scanner.py`:

```python
def _find_compose_file(path: str):
    """Find docker-compose.yml or compose.yml in the given directory."""
    for name in ('docker-compose.yml', 'docker-compose.yaml', 'compose.yml', 'compose.yaml'):
        filepath = os.path.join(path, name)
        if os.path.isfile(filepath):
            return filepath
    return None


def _parse_port_string(port_str: str) -> dict:
    """Parse a Docker compose short-syntax port string like '8080:80' or '127.0.0.1:8080:80/udp'."""
    protocol = 'tcp'
    if '/' in port_str:
        port_str, protocol = port_str.rsplit('/', 1)

    parts = port_str.split(':')
    if len(parts) == 1:
        # Just container port, e.g., "3000"
        return {
            'host_port': None,
            'container_port': int(parts[0]),
            'protocol': protocol,
            'bind_address': '0.0.0.0',
        }
    elif len(parts) == 2:
        # host:container, e.g., "8080:80"
        return {
            'host_port': int(parts[0]),
            'container_port': int(parts[1]),
            'protocol': protocol,
            'bind_address': '0.0.0.0',
        }
    elif len(parts) == 3:
        # bind:host:container, e.g., "127.0.0.1:8080:80"
        return {
            'host_port': int(parts[1]),
            'container_port': int(parts[2]),
            'protocol': protocol,
            'bind_address': parts[0],
        }
    return None


def get_compose_ports(path: str) -> list:
    """Parse compose file and extract port mappings per service."""
    if yaml is None:
        return []

    compose_file = _find_compose_file(path)
    if compose_file is None:
        return []

    with open(compose_file, 'r') as f:
        data = yaml.safe_load(f)

    if not data or 'services' not in data:
        return []

    result = []
    for service_name, service_config in data['services'].items():
        ports = []
        for port_def in service_config.get('ports', []):
            if isinstance(port_def, dict):
                # Long syntax
                ports.append({
                    'host_port': int(port_def['published']) if port_def.get('published') else None,
                    'container_port': int(port_def['target']),
                    'protocol': port_def.get('protocol', 'tcp'),
                    'bind_address': port_def.get('host_ip', '0.0.0.0'),
                })
            else:
                # Short syntax (string or int)
                parsed = _parse_port_string(str(port_def))
                if parsed:
                    ports.append(parsed)

        result.append({
            'service': service_name,
            'image': service_config.get('image', ''),
            'ports': ports,
            'compose_file': compose_file,
        })
    return result
```

**Step 4: Wire into main()**

```python
    compose_services = get_compose_ports(os.path.abspath(args.path))
    result['compose_services'] = compose_services
```

**Step 5: Run test to verify it passes**

Run: `cd port-authhority && python -m pytest tests/test_port_scanner.py -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add scripts/port_scanner.py tests/test_port_scanner.py
git commit -m "feat: add get_compose_ports() with short and long syntax parsing"
```

---

### Task 6: Implement get_host_ports()

**Files:**
- Modify: `scripts/port_scanner.py`
- Modify: `tests/test_port_scanner.py`

**Step 1: Write the tests**

Add to `tests/test_port_scanner.py`:

```python
from port_scanner import get_host_ports, _parse_ss_output, _parse_lsof_output, _parse_netstat_output


class TestGetHostPorts(unittest.TestCase):
    def test_parse_ss_output(self):
        output = """State  Recv-Q Send-Q Local Address:Port  Peer Address:Port Process
LISTEN 0      128          0.0.0.0:22         0.0.0.0:*     users:(("sshd",pid=1234,fd=3))
LISTEN 0      511        127.0.0.1:3000       0.0.0.0:*     users:(("node",pid=5678,fd=18))
"""
        ports = _parse_ss_output(output)
        self.assertEqual(len(ports), 2)
        self.assertEqual(ports[0]['port'], 22)
        self.assertEqual(ports[0]['bind_address'], '0.0.0.0')
        self.assertEqual(ports[0]['process'], 'sshd')
        self.assertEqual(ports[0]['pid'], 1234)
        self.assertEqual(ports[1]['port'], 3000)
        self.assertEqual(ports[1]['bind_address'], '127.0.0.1')
        self.assertEqual(ports[1]['process'], 'node')

    def test_parse_lsof_output(self):
        output = """COMMAND   PID USER   FD   TYPE DEVICE SIZE/OFF NODE NAME
node     1234 user   18u  IPv4  12345      0t0  TCP *:3000 (LISTEN)
postgres 5678 user    5u  IPv4  12346      0t0  TCP 127.0.0.1:5432 (LISTEN)
"""
        ports = _parse_lsof_output(output)
        self.assertEqual(len(ports), 2)
        self.assertEqual(ports[0]['port'], 3000)
        self.assertEqual(ports[0]['process'], 'node')
        self.assertEqual(ports[0]['pid'], 1234)
        self.assertEqual(ports[0]['bind_address'], '0.0.0.0')
        self.assertEqual(ports[1]['port'], 5432)
        self.assertEqual(ports[1]['bind_address'], '127.0.0.1')

    def test_parse_netstat_output(self):
        output = """  Proto  Local Address          Foreign Address        State           PID
  TCP    0.0.0.0:135            0.0.0.0:0              LISTENING       1020
  TCP    127.0.0.1:3000         0.0.0.0:0              LISTENING       5678
"""
        ports = _parse_netstat_output(output, {'1020': 'svchost.exe', '5678': 'node.exe'})
        self.assertEqual(len(ports), 2)
        self.assertEqual(ports[0]['port'], 135)
        self.assertEqual(ports[0]['process'], 'svchost.exe')
        self.assertEqual(ports[1]['port'], 3000)
        self.assertEqual(ports[1]['process'], 'node.exe')


if __name__ == '__main__':
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `cd port-authhority && python -m pytest tests/test_port_scanner.py::TestGetHostPorts -v`
Expected: FAIL

**Step 3: Implement the parsing functions and get_host_ports()**

Add to `scripts/port_scanner.py`:

```python
import re


def _parse_ss_output(output: str) -> list:
    """Parse Linux `ss -tlnp` output."""
    ports = []
    for line in output.strip().splitlines()[1:]:  # skip header
        parts = line.split()
        if len(parts) < 5 or parts[0] != 'LISTEN':
            continue
        local = parts[3]
        # Handle IPv6 [::]:port and IPv4 addr:port
        if ']:' in local:
            bind_addr, port_str = local.rsplit(':', 1)
            bind_addr = bind_addr.strip('[]')
        else:
            bind_addr, port_str = local.rsplit(':', 1)
        try:
            port = int(port_str)
        except ValueError:
            continue

        process_name = ''
        pid = 0
        process_info = ' '.join(parts[5:]) if len(parts) > 5 else ''
        m = re.search(r'\("(\w+)",pid=(\d+)', process_info)
        if m:
            process_name = m.group(1)
            pid = int(m.group(2))

        ports.append({
            'port': port,
            'protocol': 'tcp',
            'pid': pid,
            'process': process_name,
            'bind_address': bind_addr,
        })
    return ports


def _parse_lsof_output(output: str) -> list:
    """Parse macOS `lsof -iTCP -sTCP:LISTEN -P -n` output."""
    ports = []
    for line in output.strip().splitlines()[1:]:  # skip header
        parts = line.split()
        if len(parts) < 9:
            continue
        process_name = parts[0]
        pid = int(parts[1])
        name_field = parts[8]  # e.g., "*:3000" or "127.0.0.1:5432"
        if ':' not in name_field:
            continue
        addr, port_str = name_field.rsplit(':', 1)
        try:
            port = int(port_str)
        except ValueError:
            continue
        bind_addr = '0.0.0.0' if addr == '*' else addr

        ports.append({
            'port': port,
            'protocol': 'tcp',
            'pid': pid,
            'process': process_name,
            'bind_address': bind_addr,
        })
    return ports


def _parse_netstat_output(output: str, pid_map: dict) -> list:
    """Parse Windows `netstat -ano` output."""
    ports = []
    for line in output.strip().splitlines():
        line = line.strip()
        if not line.startswith('TCP') and not line.startswith('UDP'):
            continue
        parts = line.split()
        if len(parts) < 4:
            continue
        protocol = parts[0].lower()
        local = parts[1]
        state = parts[2] if protocol == 'tcp' else ''
        if protocol == 'tcp' and state != 'LISTENING':
            continue

        pid_str = parts[-1]
        addr, port_str = local.rsplit(':', 1)
        try:
            port = int(port_str)
        except ValueError:
            continue

        ports.append({
            'port': port,
            'protocol': protocol,
            'pid': int(pid_str) if pid_str.isdigit() else 0,
            'process': pid_map.get(pid_str, ''),
            'bind_address': addr,
        })
    return ports


def _get_windows_pid_map() -> dict:
    """Get PID-to-process-name map from tasklist on Windows."""
    try:
        output = subprocess.check_output(
            ['tasklist', '/FO', 'CSV', '/NH'],
            text=True, stderr=subprocess.DEVNULL
        )
        pid_map = {}
        for line in output.strip().splitlines():
            parts = line.strip('"').split('","')
            if len(parts) >= 2:
                name = parts[0]
                pid = parts[1]
                pid_map[pid] = name
        return pid_map
    except Exception:
        return {}


def get_host_ports() -> list:
    """Get all listening ports on the host, cross-platform."""
    plat = detect_platform()
    try:
        if plat == 'linux':
            output = subprocess.check_output(
                ['ss', '-tlnp'], text=True, stderr=subprocess.DEVNULL
            )
            return _parse_ss_output(output)
        elif plat == 'darwin':
            output = subprocess.check_output(
                ['lsof', '-iTCP', '-sTCP:LISTEN', '-P', '-n'],
                text=True, stderr=subprocess.DEVNULL
            )
            return _parse_lsof_output(output)
        elif plat == 'windows':
            output = subprocess.check_output(
                ['netstat', '-ano'], text=True, stderr=subprocess.DEVNULL
            )
            pid_map = _get_windows_pid_map()
            return _parse_netstat_output(output, pid_map)
    except Exception:
        return []
    return []
```

**Step 4: Wire into main()**

```python
    host_ports = get_host_ports()
    result['host_ports'] = host_ports
```

**Step 5: Run test to verify it passes**

Run: `cd port-authhority && python -m pytest tests/test_port_scanner.py -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add scripts/port_scanner.py tests/test_port_scanner.py
git commit -m "feat: add get_host_ports() with cross-platform parsing"
```

---

### Task 7: Implement analyze_conflicts()

**Files:**
- Modify: `scripts/port_scanner.py`
- Modify: `tests/test_port_scanner.py`

**Step 1: Write the tests**

Add to `tests/test_port_scanner.py`:

```python
from port_scanner import analyze_conflicts


class TestAnalyzeConflicts(unittest.TestCase):
    def test_container_host_conflict(self):
        containers = [{'id': 'abc', 'name': 'web', 'image': 'nginx', 'state': 'running',
                        'ports': [{'host_port': 3000, 'container_port': 80, 'protocol': 'tcp', 'bind_address': '0.0.0.0'}]}]
        host_ports = [{'port': 3000, 'protocol': 'tcp', 'pid': 1234, 'process': 'node', 'bind_address': '0.0.0.0'}]
        conflicts = analyze_conflicts(containers, [], host_ports)
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]['type'], 'container-host')
        self.assertEqual(conflicts[0]['port'], 3000)
        self.assertIn('container:web', conflicts[0]['parties'])
        self.assertIn('process:node(PID 1234)', conflicts[0]['parties'])
        self.assertIsNotNone(conflicts[0]['suggestion'])

    def test_container_container_conflict(self):
        containers = [
            {'id': 'abc', 'name': 'web1', 'image': 'nginx', 'state': 'running',
             'ports': [{'host_port': 8080, 'container_port': 80, 'protocol': 'tcp', 'bind_address': '0.0.0.0'}]},
            {'id': 'def', 'name': 'web2', 'image': 'nginx', 'state': 'running',
             'ports': [{'host_port': 8080, 'container_port': 80, 'protocol': 'tcp', 'bind_address': '0.0.0.0'}]},
        ]
        conflicts = analyze_conflicts(containers, [], [])
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]['type'], 'container-container')

    def test_compose_pending_conflict(self):
        host_ports = [{'port': 5432, 'protocol': 'tcp', 'pid': 999, 'process': 'postgres', 'bind_address': '0.0.0.0'}]
        compose = [{'service': 'db', 'image': 'postgres', 'compose_file': 'docker-compose.yml',
                     'ports': [{'host_port': 5432, 'container_port': 5432, 'protocol': 'tcp', 'bind_address': '0.0.0.0'}]}]
        conflicts = analyze_conflicts([], compose, host_ports)
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]['type'], 'compose-pending')

    def test_no_conflict_different_ports(self):
        containers = [{'id': 'abc', 'name': 'web', 'image': 'nginx', 'state': 'running',
                        'ports': [{'host_port': 3000, 'container_port': 80, 'protocol': 'tcp', 'bind_address': '0.0.0.0'}]}]
        host_ports = [{'port': 5000, 'protocol': 'tcp', 'pid': 1234, 'process': 'flask', 'bind_address': '0.0.0.0'}]
        conflicts = analyze_conflicts(containers, [], host_ports)
        self.assertEqual(len(conflicts), 0)

    def test_no_conflict_different_bind_addresses(self):
        """127.0.0.1:3000 and 192.168.1.5:3000 should NOT conflict."""
        containers = [{'id': 'abc', 'name': 'web', 'image': 'nginx', 'state': 'running',
                        'ports': [{'host_port': 3000, 'container_port': 80, 'protocol': 'tcp', 'bind_address': '127.0.0.1'}]}]
        host_ports = [{'port': 3000, 'protocol': 'tcp', 'pid': 1234, 'process': 'node', 'bind_address': '192.168.1.5'}]
        conflicts = analyze_conflicts(containers, [], host_ports)
        self.assertEqual(len(conflicts), 0)

    def test_conflict_when_one_binds_all(self):
        """0.0.0.0:3000 conflicts with 127.0.0.1:3000."""
        containers = [{'id': 'abc', 'name': 'web', 'image': 'nginx', 'state': 'running',
                        'ports': [{'host_port': 3000, 'container_port': 80, 'protocol': 'tcp', 'bind_address': '0.0.0.0'}]}]
        host_ports = [{'port': 3000, 'protocol': 'tcp', 'pid': 1234, 'process': 'node', 'bind_address': '127.0.0.1'}]
        conflicts = analyze_conflicts(containers, [], host_ports)
        self.assertEqual(len(conflicts), 1)

    def test_no_conflict_different_protocols(self):
        containers = [{'id': 'abc', 'name': 'web', 'image': 'nginx', 'state': 'running',
                        'ports': [{'host_port': 3000, 'container_port': 80, 'protocol': 'tcp', 'bind_address': '0.0.0.0'}]}]
        host_ports = [{'port': 3000, 'protocol': 'udp', 'pid': 1234, 'process': 'dns', 'bind_address': '0.0.0.0'}]
        conflicts = analyze_conflicts(containers, [], host_ports)
        self.assertEqual(len(conflicts), 0)

    def test_suggestion_finds_next_available_port(self):
        host_ports = [
            {'port': 3000, 'protocol': 'tcp', 'pid': 1, 'process': 'a', 'bind_address': '0.0.0.0'},
            {'port': 3001, 'protocol': 'tcp', 'pid': 2, 'process': 'b', 'bind_address': '0.0.0.0'},
        ]
        containers = [{'id': 'abc', 'name': 'web', 'image': 'nginx', 'state': 'running',
                        'ports': [{'host_port': 3000, 'container_port': 80, 'protocol': 'tcp', 'bind_address': '0.0.0.0'}]}]
        conflicts = analyze_conflicts(containers, [], host_ports)
        self.assertEqual(len(conflicts), 1)
        # 3000 and 3001 are taken, so suggestion should be 3002
        self.assertIn('3002', conflicts[0]['suggestion'])
```

**Step 2: Run test to verify it fails**

Run: `cd port-authhority && python -m pytest tests/test_port_scanner.py::TestAnalyzeConflicts -v`
Expected: FAIL

**Step 3: Implement analyze_conflicts()**

Add to `scripts/port_scanner.py`:

```python
def _addresses_conflict(addr1: str, addr2: str) -> bool:
    """Check if two bind addresses conflict. 0.0.0.0 and :: conflict with everything."""
    wildcard = {'0.0.0.0', '::', '*', ''}
    if addr1 in wildcard or addr2 in wildcard:
        return True
    return addr1 == addr2


def _find_available_port(port: int, used_ports: set) -> int:
    """Find the nearest available port starting from the given port."""
    candidate = port + 1
    while candidate in used_ports and candidate < 65535:
        candidate += 1
    return candidate


def analyze_conflicts(containers: list, compose_services: list, host_ports: list) -> list:
    """Cross-reference all port sources and find conflicts."""
    conflicts = []

    # Collect all used ports for suggestion generation
    all_used = set()
    for c in containers:
        for p in c['ports']:
            all_used.add(p['host_port'])
    for h in host_ports:
        all_used.add(h['port'])
    for s in compose_services:
        for p in s['ports']:
            if p['host_port'] is not None:
                all_used.add(p['host_port'])

    # Container vs host process conflicts
    for c in containers:
        for cp in c['ports']:
            for hp in host_ports:
                if (cp['host_port'] == hp['port']
                        and cp['protocol'] == hp['protocol']
                        and _addresses_conflict(cp['bind_address'], hp['bind_address'])):
                    available = _find_available_port(cp['host_port'], all_used)
                    conflicts.append({
                        'type': 'container-host',
                        'port': cp['host_port'],
                        'protocol': cp['protocol'],
                        'parties': [
                            f"container:{c['name']}",
                            f"process:{hp['process']}(PID {hp['pid']})",
                        ],
                        'suggestion': f"Use port {available} (available)",
                    })

    # Container vs container conflicts
    seen = []
    for c in containers:
        for cp in c['ports']:
            for prev_c, prev_p in seen:
                if (cp['host_port'] == prev_p['host_port']
                        and cp['protocol'] == prev_p['protocol']
                        and _addresses_conflict(cp['bind_address'], prev_p['bind_address'])):
                    available = _find_available_port(cp['host_port'], all_used)
                    conflicts.append({
                        'type': 'container-container',
                        'port': cp['host_port'],
                        'protocol': cp['protocol'],
                        'parties': [
                            f"container:{prev_c['name']}",
                            f"container:{c['name']}",
                        ],
                        'suggestion': f"Use port {available} (available)",
                    })
            seen.append((c, cp))

    # Compose pending conflicts (compose port vs existing host/container port)
    for s in compose_services:
        for sp in s['ports']:
            if sp['host_port'] is None:
                continue
            for hp in host_ports:
                if (sp['host_port'] == hp['port']
                        and sp['protocol'] == hp['protocol']
                        and _addresses_conflict(sp['bind_address'], hp['bind_address'])):
                    available = _find_available_port(sp['host_port'], all_used)
                    conflicts.append({
                        'type': 'compose-pending',
                        'port': sp['host_port'],
                        'protocol': sp['protocol'],
                        'parties': [
                            f"compose:{s['service']}",
                            f"process:{hp['process']}(PID {hp['pid']})",
                        ],
                        'suggestion': f"Use port {available} (available)",
                    })
            for c in containers:
                for cp in c['ports']:
                    if (sp['host_port'] == cp['host_port']
                            and sp['protocol'] == cp['protocol']
                            and _addresses_conflict(sp['bind_address'], cp['bind_address'])):
                        available = _find_available_port(sp['host_port'], all_used)
                        conflicts.append({
                            'type': 'compose-pending',
                            'port': sp['host_port'],
                            'protocol': sp['protocol'],
                            'parties': [
                                f"compose:{s['service']}",
                                f"container:{c['name']}",
                            ],
                            'suggestion': f"Use port {available} (available)",
                        })

    return conflicts
```

**Step 4: Wire into main()**

```python
    conflicts = analyze_conflicts(containers, compose_services, host_ports)
    result['conflicts'] = conflicts
    total_ports = set()
    for c in containers:
        for p in c['ports']:
            total_ports.add(p['host_port'])
    for h in host_ports:
        total_ports.add(h['port'])
    result['summary'] = {
        'total_ports': len(total_ports),
        'conflicts': len(conflicts),
        'containers': len(containers),
    }
```

**Step 5: Run test to verify it passes**

Run: `cd port-authhority && python -m pytest tests/test_port_scanner.py -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add scripts/port_scanner.py tests/test_port_scanner.py
git commit -m "feat: add analyze_conflicts() with bind-address and protocol awareness"
```

---

### Task 8: Add WSL2 detection and cross-context scanning

**Files:**
- Modify: `scripts/port_scanner.py`
- Modify: `tests/test_port_scanner.py`

**Step 1: Write the test**

Add to `tests/test_port_scanner.py`:

```python
from port_scanner import is_wsl, get_wsl_host_ports


class TestWSL(unittest.TestCase):
    @patch('os.path.exists', return_value=True)
    @patch('platform.system', return_value='Linux')
    def test_wsl_detected(self, mock_sys, mock_exists):
        self.assertTrue(is_wsl())

    @patch('os.path.exists', return_value=False)
    @patch('platform.system', return_value='Linux')
    def test_wsl_not_detected_on_native_linux(self, mock_sys, mock_exists):
        self.assertFalse(is_wsl())

    @patch('platform.system', return_value='Darwin')
    def test_wsl_not_on_macos(self, mock_sys):
        self.assertFalse(is_wsl())

    @patch('subprocess.check_output')
    def test_get_wsl_host_ports(self, mock_subprocess):
        mock_subprocess.return_value = """  Proto  Local Address          Foreign Address        State           PID
  TCP    0.0.0.0:3000           0.0.0.0:0              LISTENING       1234
"""
        ports = get_wsl_host_ports({'1234': 'node.exe'})
        self.assertEqual(len(ports), 1)
        self.assertEqual(ports[0]['port'], 3000)
```

**Step 2: Run test to verify it fails**

Run: `cd port-authhority && python -m pytest tests/test_port_scanner.py::TestWSL -v`
Expected: FAIL

**Step 3: Implement WSL detection**

Add to `scripts/port_scanner.py`:

```python
def is_wsl() -> bool:
    """Detect if running inside WSL."""
    if platform.system() != 'Linux':
        return False
    return os.path.exists('/proc/sys/fs/binfmt_misc/WSLInterop') or os.path.exists('/run/WSL')


def get_wsl_host_ports(pid_map: dict = None) -> list:
    """From inside WSL, get Windows host listening ports via netstat.exe."""
    try:
        output = subprocess.check_output(
            ['netstat.exe', '-ano'], text=True, stderr=subprocess.DEVNULL
        )
        if pid_map is None:
            try:
                tasklist_output = subprocess.check_output(
                    ['tasklist.exe', '/FO', 'CSV', '/NH'],
                    text=True, stderr=subprocess.DEVNULL
                )
                pid_map = {}
                for line in tasklist_output.strip().splitlines():
                    parts = line.strip('"').split('","')
                    if len(parts) >= 2:
                        pid_map[parts[1]] = parts[0]
            except Exception:
                pid_map = {}
        return _parse_netstat_output(output, pid_map)
    except Exception:
        return []
```

**Step 4: Update get_host_ports() to include WSL cross-context**

Add at the end of `get_host_ports()`, before the final `return`:

```python
    # If running in WSL, also check Windows host ports
    if is_wsl():
        try:
            wsl_ports = get_wsl_host_ports()
            # Mark these as coming from Windows host
            for p in wsl_ports:
                p['source'] = 'windows-host'
            result = ports  # rename the linux ports variable
            for p in result:
                p['source'] = 'wsl'
            result.extend(wsl_ports)
            return result
        except Exception:
            pass
```

Note: This requires restructuring `get_host_ports()` slightly so the Linux branch stores its result in a variable before returning. The implementation should capture the Linux ports into a `ports` variable, then check for WSL and extend.

**Step 5: Run test to verify it passes**

Run: `cd port-authhority && python -m pytest tests/test_port_scanner.py -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add scripts/port_scanner.py tests/test_port_scanner.py
git commit -m "feat: add WSL2 detection and cross-context port scanning"
```

---

### Task 9: Final integration — complete main() and end-to-end test

**Files:**
- Modify: `scripts/port_scanner.py`
- Modify: `tests/test_port_scanner.py`

**Step 1: Write the integration test**

Add to `tests/test_port_scanner.py`:

```python
class TestMainIntegration(unittest.TestCase):
    @patch('port_scanner.get_host_ports')
    @patch('port_scanner.get_compose_ports')
    @patch('port_scanner.get_docker_containers')
    @patch('port_scanner.is_docker_desktop', return_value=False)
    @patch('port_scanner.detect_platform', return_value='linux')
    def test_main_outputs_valid_json(self, mock_plat, mock_dd, mock_docker, mock_compose, mock_host):
        mock_docker.return_value = [
            {'id': 'abc', 'name': 'web', 'image': 'nginx', 'state': 'running',
             'ports': [{'host_port': 8080, 'container_port': 80, 'protocol': 'tcp', 'bind_address': '0.0.0.0'}]}
        ]
        mock_compose.return_value = []
        mock_host.return_value = [
            {'port': 8080, 'protocol': 'tcp', 'pid': 1234, 'process': 'apache', 'bind_address': '0.0.0.0'}
        ]

        import io
        from contextlib import redirect_stdout
        from port_scanner import main

        f = io.StringIO()
        with redirect_stdout(f), patch('sys.argv', ['port_scanner.py', '--path', '.']):
            main()

        output = json.loads(f.getvalue())
        self.assertEqual(output['platform'], 'linux')
        self.assertFalse(output['docker_desktop'])
        self.assertEqual(len(output['containers']), 1)
        self.assertEqual(len(output['conflicts']), 1)
        self.assertEqual(output['conflicts'][0]['type'], 'container-host')
        self.assertEqual(output['summary']['conflicts'], 1)
        self.assertEqual(output['summary']['containers'], 1)
```

**Step 2: Run test to verify it passes**

Run: `cd port-authhority && python -m pytest tests/test_port_scanner.py -v`
Expected: All tests PASS (main() should already work from previous wiring)

**Step 3: Commit**

```bash
git add tests/test_port_scanner.py
git commit -m "test: add integration test for main() JSON output"
```

---

### Task 10: Manual smoke test

**Files:** None (verification only)

**Step 1: Run the script directly**

Run: `cd port-authhority && python scripts/port_scanner.py --path .`

Expected: Valid JSON output to stdout with the current system's port state. Verify:
- `platform` matches your OS
- `docker_desktop` is boolean
- `containers` lists any running Docker containers
- `host_ports` lists listening ports
- `conflicts` shows any actual conflicts
- `summary` has correct counts

**Step 2: Run full test suite**

Run: `cd port-authhority && python -m pytest tests/ -v --tb=short`

Expected: All tests PASS

**Step 3: Final commit if any fixes were needed**

```bash
git add -A
git commit -m "fix: address issues found during smoke testing"
```

---

### Task 11: Commit all files and verify skill structure

**Step 1: Verify final structure**

Run: `find port-authhority -type f | sort` (or `ls -R` on Windows)

Expected:
```
port-authhority/SKILL.md
port-authhority/docs/plans/2026-03-01-port-authhority-design.md
port-authhority/docs/plans/2026-03-01-port-authhority-implementation.md
port-authhority/references/common-ports.md
port-authhority/scripts/port_scanner.py
port-authhority/tests/test_port_scanner.py
```

**Step 2: Final commit**

```bash
git add -A
git commit -m "feat: complete port-authhority skill — Docker port conflict manager"
```
