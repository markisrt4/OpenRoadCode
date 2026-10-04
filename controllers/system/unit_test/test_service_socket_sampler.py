# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Validate attribution and traffic rates without requiring privileged sockets."""

import subprocess
import tempfile
import unittest
from pathlib import Path

from controllers.system.service_socket_parser import parse_socket_table, parse_tcp_counters, counter_rate
from controllers.system.service_socket_sampler import ServiceSocketSampler
from ui.system_diagnostics import OrcProcessSnapshot, OrcWorkloadSnapshot


HEADER = 'sl local_address rem_address st tx_queue:rx_queue tr tm retrnsmt uid timeout inode\n'


def table(protocol='TCP', *, inode=500, state='01', tx=0, rx=0, drops=0, ipv6=False):
    local = '00000000000000000000000001000000' if ipv6 else '0100007F'
    remote = '00000000000000000000000000000000' if ipv6 else '0200007F'
    return HEADER + f'0: {local}:15B4 {remote}:C350 {state} {tx:08X}:{rx:08X} 00:00000000 00000000 1000 0 {inode} 1 0000 {drops}\n'


class ParserTests(unittest.TestCase):
    def test_ipv4_ipv6_states_and_queues(self):
        row = parse_socket_table(table(tx=128, rx=256), 'TCP')[0]
        self.assertEqual((row.local, row.remote), ('127.0.0.1:5556', '127.0.0.2:50000'))
        self.assertEqual((row.state, row.tx_queue, row.rx_queue), ('connected', 128, 256))
        self.assertEqual(parse_socket_table(table(state='0A'), 'TCP')[0].state, 'listening')
        self.assertEqual(parse_socket_table(table(ipv6=True), 'TCP')[0].local, '[::1]:5556')
        self.assertEqual(parse_socket_table(table(protocol='UDP', state='07', drops=8), 'UDP')[0].drops, 8)

    def test_malformed_rows_and_inode_zero_are_ignored(self):
        self.assertEqual(parse_socket_table(HEADER + 'bad row\n' + table(inode=0).splitlines()[1], 'TCP'), ())

    def test_ss_missing_counters_are_not_reported_as_zero(self):
        rows = parse_tcp_counters('ESTAB 0 0 x y ino:500 sk:a1 bytes_sent:300 bytes_received:200\nLISTEN 0 4096 x y ino:501 sk:a2\n')
        self.assertEqual(rows[500], ('a1', 200, 300))
        self.assertEqual(rows[501], ('a2', None, None))
        self.assertIsNone(counter_rate(10, 20, 1))
        self.assertIsNone(counter_rate(10, None, 1))
        self.assertIsNone(counter_rate(10, 0, 0))


class SamplerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'self/ns').mkdir(parents=True)
        (self.root / 'self/ns/net').symlink_to('net:[1]')
        self.pid = self.root / '10'
        for name in ('fd', 'net', 'ns'):
            (self.pid / name).mkdir(parents=True)
        (self.pid / 'ns/net').symlink_to('net:[1]')
        (self.pid / 'fd/3').symlink_to('socket:[500]')
        # A duplicate descriptor must not double the endpoint's rates.
        (self.pid / 'fd/4').symlink_to('socket:[500]')
        for name in ('tcp', 'tcp6', 'udp', 'udp6'):
            (self.pid / 'net' / name).write_text(HEADER)
        (self.pid / 'net/tcp').write_text(table())
        self.now = 0
        self.counter_text = 'ESTAB 0 0 x y ino:500 sk:a1 bytes_sent:0 bytes_received:0'
        self.sampler = ServiceSocketSampler(self.root, monotonic=lambda: self.now, tcp_reader=lambda: self.counter_text)
        self.work = OrcWorkloadSnapshot(visibility='visible', processes=(
            OrcProcessSnapshot(10, 'messaging.zeromq.broker_cli', 'workload', 'S'),))

    def live(self, rows):
        return [row for row in rows if row.pid is not None]

    def test_tcp_delta_rates_and_duplicate_fd(self):
        rows = self.live(self.sampler.sample(self.work))
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0].receive_bytes_per_second)
        self.now = 2
        self.counter_text = 'ESTAB 0 0 x y ino:500 sk:a1 bytes_sent:300 bytes_received:200'
        row = self.live(self.sampler.sample(self.work))[0]
        self.assertEqual((row.receive_bytes_per_second, row.transmit_bytes_per_second), (100, 150))
        self.assertEqual(row.name, 'Message broker')

    def test_cookie_change_and_counter_reset_do_not_make_false_rates(self):
        self.sampler.sample(self.work)
        self.now = 1
        self.counter_text = 'ESTAB 0 0 x y ino:500 sk:a2 bytes_sent:500 bytes_received:500'
        self.assertIsNone(self.live(self.sampler.sample(self.work))[0].receive_bytes_per_second)
        self.now = 2
        self.counter_text = 'ESTAB 0 0 x y ino:500 sk:a2 bytes_sent:100 bytes_received:100'
        self.assertIsNone(self.live(self.sampler.sample(self.work))[0].receive_bytes_per_second)

    def test_udp_queues_are_not_bandwidth_and_drop_alert_recovers(self):
        (self.pid / 'net/tcp').write_text(HEADER)
        (self.pid / 'net/udp').write_text(table(protocol='UDP', state='07', tx=1024, rx=2048, drops=10))
        row = self.live(self.sampler.sample(self.work))[0]
        self.assertEqual(row.state, 'bound')  # Historical drops are not a current failure.
        self.now = 1
        (self.pid / 'net/udp').write_text(table(protocol='UDP', state='07', tx=4096, rx=8192, drops=12))
        row = self.live(self.sampler.sample(self.work))[0]
        self.assertEqual((row.state, row.drops_per_second), ('dropping', 2))
        self.assertIsNone(row.receive_bytes_per_second)
        self.assertIsNone(row.transmit_bytes_per_second)
        self.now = 2
        self.assertEqual(self.live(self.sampler.sample(self.work))[0].state, 'bound')

    def test_counters_from_other_namespace_are_not_attributed(self):
        (self.pid / 'ns/net').unlink()
        (self.pid / 'ns/net').symlink_to('net:[2]')
        self.sampler.sample(self.work)
        self.now = 1
        self.counter_text = 'ESTAB 0 0 x y ino:500 sk:a1 bytes_sent:500 bytes_received:500'
        self.assertIsNone(self.live(self.sampler.sample(self.work))[0].receive_bytes_per_second)

    def test_unowned_sockets_and_unobserved_optional_services(self):
        (self.pid / 'net/tcp').write_text(table(inode=999))
        rows = self.sampler.sample(self.work)
        self.assertEqual(self.live(rows)[0].state, 'no_socket')
        self.assertTrue(any(row.name == 'Navigation' and row.state == 'not_observed' for row in rows))

    def test_restricted_socket_files_leave_health_unknown(self):
        (self.pid / 'net/tcp').unlink()
        rows = self.sampler.sample(self.work)
        self.assertEqual(self.live(rows)[0].state, 'unavailable')
        self.assertIn('restricted', self.sampler.status)

    def test_ss_failure_preserves_socket_states_and_missing_rates(self):
        def fail():
            raise subprocess.TimeoutExpired('ss', 0.5)
        sampler = ServiceSocketSampler(self.root, tcp_reader=fail)
        row = self.live(sampler.sample(self.work))[0]
        self.assertEqual(row.state, 'connected')
        self.assertIsNone(row.transmit_bytes_per_second)
        self.assertIn('TCP byte counters unavailable', sampler.status)

    def test_endpoint_limit_and_stopped_process(self):
        sampler = ServiceSocketSampler(self.root, tcp_reader=lambda: '', max_rows=1)
        self.assertEqual(len(sampler.sample(self.work)), 1)
        self.assertIn('Showing 1', sampler.status)
        work = OrcWorkloadSnapshot(processes=(OrcProcessSnapshot(10, 'messaging.zeromq.broker_cli', 'workload', 'Z'),))
        self.assertEqual(self.live(self.sampler.sample(work))[0].state, 'stopped')
