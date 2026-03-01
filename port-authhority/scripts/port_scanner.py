#!/usr/bin/env python3
"""Port Authhority - Docker port conflict scanner.

Detects port conflicts between Docker containers, compose services,
and host processes. Outputs structured JSON for Claude to interpret.
"""

import argparse
import json
import os
import platform
import re
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

    # Skip port range syntax (e.g., "8000-8010:8000-8010") — not supported
    if '-' in port_str:
        return None

    parts = port_str.split(':')
    try:
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
    except ValueError:
        return None
    return None


def get_compose_ports(path: str) -> list:
    """Parse compose file and extract port mappings per service."""
    if yaml is None:
        return []

    compose_file = _find_compose_file(path)
    if compose_file is None:
        return []

    with open(compose_file, 'r', encoding='utf-8') as f:
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
        m = re.search(r'\("([^"]+)",pid=(\d+)', process_info)
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
        if len(parts) < 5:
            continue
        protocol = parts[0].lower()
        local = parts[1]
        # netstat -ano columns: Proto, Local Address, Foreign Address, State, PID
        state = parts[3] if protocol == 'tcp' else ''
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
            ports = _parse_ss_output(output)
            # If running in WSL, also check Windows host ports
            if is_wsl():
                try:
                    wsl_ports = get_wsl_host_ports()
                    for p in wsl_ports:
                        p['source'] = 'windows-host'
                    for p in ports:
                        p['source'] = 'wsl'
                    ports.extend(wsl_ports)
                except Exception:
                    pass
            return ports
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


def _addresses_conflict(addr1: str, addr2: str) -> bool:
    """Check if two bind addresses conflict. 0.0.0.0 and :: conflict with everything."""
    wildcard = {'0.0.0.0', '::', '*', ''}
    if addr1 in wildcard or addr2 in wildcard:
        return True
    return addr1 == addr2


def _find_available_port(port: int, used_ports: set) -> int:
    """Find the nearest available port starting from the given port."""
    candidate = port + 1
    while candidate in used_ports and candidate <= 65535:
        candidate += 1
    if candidate > 65535:
        return 0  # no available port found
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

    containers = get_docker_containers()
    result['containers'] = containers

    compose_services = get_compose_ports(os.path.abspath(args.path))
    result['compose_services'] = compose_services

    host_ports = get_host_ports()
    result['host_ports'] = host_ports

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

    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
