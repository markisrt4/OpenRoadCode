# Security Policy

OpenRoadCode connects software to vehicles, radios, Bluetooth devices, Linux
services, and third-party APIs. Responsible security reports help keep that
experimentation enjoyable for everyone.

## Reporting a vulnerability

Please do not open a public issue for a vulnerability that could expose
credentials, private data, a vehicle, or a system running OpenRoadCode.

For a sensitive report, contact the maintainer privately using the contact
information published at [openroadcode.org](https://openroadcode.org). If a
private contact method is unavailable, open a GitHub issue containing no
technical details and ask the maintainer to arrange a private conversation.

For concerns that are not sensitive, such as a hardening suggestion with no
known exploit, a normal GitHub issue is welcome.

Include as much of the following as is safe to share:

- The affected component and revision
- The target platform and relevant hardware
- Steps needed to reproduce the behavior
- The possible impact
- Any suggested mitigation

Please remove OAuth tokens, API keys, Bluetooth addresses, precise location
history, vehicle identifiers, and other private data from reports and logs.

The maintainer will acknowledge a private report as soon as practical, work
with the reporter to understand its impact, and coordinate disclosure after a
fix or mitigation is available. Response times are best-effort while the
project is maintained by a small team.

## Supported versions

OpenRoadCode is currently pre-release software. Security fixes are made on the
default branch; older commits and experimental branches are not supported.

## Safety and scope

OpenRoadCode is not intended for steering, braking, throttle, airbags, or any
other safety-critical vehicle function. Do not test security findings while
driving or in a way that could interfere with safe vehicle operation.

Useful reports include credential exposure, unsafe file permissions,
privilege-escalation paths, command injection, insecure network services, and
unintended disclosure of vehicle or location data. Reports about third-party
projects should be sent to their maintainers unless OpenRoadCode introduces or
amplifies the vulnerability.
