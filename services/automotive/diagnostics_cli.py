# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Request a read-only scan from the running automotive service and check a scenario."""
import argparse
import json
from config.service_runtime_config import ServiceRuntimeConfigParser
from services.automotive.automotive_service_cli import DEFAULT_RUNTIME_CONFIG
from services.automotive.automotive_command_client import AutomotiveCommandClient


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default=str(DEFAULT_RUNTIME_CONFIG))
    parser.add_argument('--endpoint')
    parser.add_argument('--expect-code')
    parser.add_argument('--expect-status', choices=('stored', 'pending', 'permanent'))
    parser.add_argument('--expect-mil', choices=('on', 'off'))
    parser.add_argument('--expect-readiness', choices=('ready', 'not-ready'))
    args = parser.parse_args()
    endpoint = args.endpoint or ServiceRuntimeConfigParser(args.config).load().automotive.command_endpoint
    result = AutomotiveCommandClient(endpoint).scan_diagnostics()
    print(json.dumps(result, indent=2))
    if args.expect_code and not any(
        item['code'] == args.expect_code.upper() and
        (args.expect_status is None or item['status'] == args.expect_status)
        for item in result['trouble_codes']
    ):
        parser.exit(1, 'Expected DTC/status was not reported\n')
    if args.expect_mil and result['mil_on'] is not (args.expect_mil == 'on'):
        parser.exit(1, 'Unexpected MIL state\n')
    if args.expect_readiness and result['emissions_ready'] is not (args.expect_readiness == 'ready'):
        parser.exit(1, 'Unexpected readiness state\n')
    if set(result.get('completed_services', [])) != {'monitor', 'stored', 'pending', 'permanent'}:
        parser.exit(1, 'Diagnostic coverage incomplete\n')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
