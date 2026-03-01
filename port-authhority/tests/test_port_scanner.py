# tests/test_port_scanner.py
import sys
import os
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from port_scanner import detect_platform, is_docker_desktop, get_docker_containers, get_compose_ports, _parse_ss_output, _parse_lsof_output, _parse_netstat_output, analyze_conflicts, is_wsl, get_wsl_host_ports


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


if __name__ == '__main__':
    unittest.main()
