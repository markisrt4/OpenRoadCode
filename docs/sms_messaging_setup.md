# Connect messaging without handling tokens

ORC Companion's **Connect messaging** button is available in Simple mode under
Connection setup → Messages, and in Advanced mode. It connects Android's SMS
gateway to the **Termux runtime on the same phone**, independently of whichever
remote ORC device is selected. It does not connect a remote desktop automatically.

## Update the phone once

In the phone's OpenRoadCode repository:

```sh
git switch feature/sms-messaging-gateway
git pull --ff-only
sv restart openroadcode-service-manager
```

Install the matching Android feature build from the Android Bridge repository:

```sh
git switch feature/sms-messaging-bridge
git pull --ff-only
development/termux/install_latest_apk.sh
```

The installer must select the exact current branch/commit's successful APK build.
Confirm the Android package update, then open ORC Companion.

## Connect or repair

1. Open Connection setup → Messages and tap **Connect messaging**.
2. Allow Android SMS reading if requested. Contacts permission remains optional
   through **Allow contacts lookup**. Sending permission is not requested by setup.
3. The phone's browser opens a page titled **Connect phone messages?**. Approve
   only if you just started setup in ORC Companion; otherwise cancel.
4. Return to ORC Companion. It verifies the Android gateway credential and shows
   **Messaging connected and verified with Termux on this phone**.

No secret is displayed or copied. No configuration editing, provisioning token,
Advanced mode, runtime pairing credential, or SMS transmission is required.
The same button repairs a stale stored Android gateway credential. Cancel or an
expired session leaves credentials unchanged unless completion was already
accepted. Setup expires after three minutes. After activity recreation or leaving
the Connection setup screen, start again; stale callbacks cannot update a new card.

If Companion says to update/restart Termux, use the commands above. The native
screen gives fixed errors for unsupported old endpoints, unavailable networking,
expired approval, and missing gateway/read permission. Browser approval alone is
not connection success: return to Companion for verified completion.

## Linux desktop after phone connection

Update TechForge and use your existing SSH tunnel. For the user's `S26Ultra` alias:

```sh
git switch feature/android-sms-bridge
git pull --ff-only
python -m techforge_messaging --check-phone-via-ssh S26Ultra
python -m techforge_messaging --import-token-from-ssh S26Ultra --config "$HOME/.config/techforge-messaging/phone-guided.env"
python -m techforge_messaging --port 18769 --config "$HOME/.config/techforge-messaging/phone-guided.env" --check-setup
```

Both phone checks should return 200; the source should be `guided connection`.
The importer selects the guided private client credential automatically and never
prints it. Use a new filename if the destination already exists; do not overwrite
an unrelated existing token file. The tunnel must still forward the VM's
127.0.0.1:18769 to the phone's 127.0.0.1:8769. Runtime pairing is unrelated.

## Protocol and storage

Only the Termux HTTP manager registers `/sms/connect/*`; Linux does not. Every
setup endpoint rejects non-loopback peers before auth/payload processing.

- POST `/sms/connect/start`: creates a three-minute SMS-only session, with separate
  random poll and browser approval capabilities. At most 16 live sessions exist.
- GET/POST `/sms/connect/approve/{id}`: displays explicit approval; POST validates
  the form capability and either approves or closes the session. Pages are
  non-cacheable, deny framing, and do not load third-party resources.
- GET `/sms/connect/status/{id}`: requires the session's poll bearer. It returns
  pending, approved, or closed. Expired sessions return 410.
- POST `/sms/connect/complete/{id}`: requires the poll bearer and prior approval,
  then authenticates the submitted Android credential against the actual fixed
  loopback gateway's `/sms/capabilities`, requiring read permission. Only then are
  private credentials saved and the session consumed. Replays are rejected.
- POST `/sms/connect/cancel/{id}`: closes the session with its poll bearer.

No runtime credential is issued or accepted by this flow. No arbitrary upstream
URL is accepted. Bodies are limited to 1024 bytes; responses never return SMS or
Android credentials. Setup invokes no contacts/messages/send route. The HTTP
handler suppresses request logs, including approval URLs. Those URLs contain only
short-lived session capabilities and should not be shared.

Approved guided setup saves `android-sms-token` and `sms-client-token` under the
private XDG OpenRoadCode Service Manager directory using existing atomic mode-0600
storage. Existing valid client credentials are preserved where possible. Their
presence makes the guided configuration authoritative and explicitly opts in to
SMS: it supersedes legacy `OPENROADCODE_SMS_ENABLED`, `OPENROADCODE_SMS_TOKEN`, and
`OPENROADCODE_ANDROID_SMS_TOKEN` overrides without a restart. Without a guided
client file, legacy behavior is unchanged. Turn off messages stops Android access;
legacy privileged credential deletion still removes the Android credential.

SSH token import and phone diagnostics must be updated alongside the guided
configuration. They prefer the saved guided credential rather than stale env
values. They do not read the running process environment or expose tokens.

## Focused validation

```sh
git switch feature/sms-messaging-gateway
python -m unittest services.common.unit_test.test_service_manager_sms_connect -v
```

The loopback tests use synthetic Android responses: approval, live credential
verification, private persistence, authenticated proxy use after repair, denial,
expiry, replay, wrong poll/pairing credentials, storage failure, session bounds,
and remote rejection. Device checks still need browser launch/return, permission
denial/grant, unavailable Termux, cancellation, activity recreation, Simple/Advanced
switching, and stale credential repair. No real SMS needs to be sent.
