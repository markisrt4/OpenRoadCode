# Linux service manager

The Linux control plane exposes the same restricted API as the Termux manager. It controls the message broker, navigation, automotive, and ADS-B (`readsb.service`) units. The core stack excludes ADS-B and starts broker, navigation, automotive in that order; stopping reverses the order.

## Security and deployment

The HTTP process runs as the dedicated `openroadcode-service-manager` system account. Status operations are unprivileged; start, stop, and restart use noninteractive sudo with an exact-unit allowlist. The installer writes `/etc/sudoers.d/openroadcode-service-manager` and validates it with `visudo`. The bearer token is stored in `/etc/openroadcode/service-manager.env` and preserved on reinstall unless explicitly overridden. Keep the token private.

The default listener is `0.0.0.0:8769`. This is intended for a trusted, isolated car LAN. HTTP does not encrypt the bearer token. Do not expose the endpoint to the internet or untrusted networks. TLS or an authenticated tunnel is deferred. Restrict access with the host/network firewall as appropriate.

## Install on Debian/systemd

From the repository root on `service-manager-linux`:

```bash
python3 -m unittest discover -s services/linux/unit_test -p 'test_*.py' -v
sudo bash scripts/systemd/install_service_manager_systemd.sh
sudo systemctl status openroadcode-service-manager --no-pager
sudo journalctl -u openroadcode-service-manager -n 50 --no-pager
```

The installer creates the service account, token file, sudoers policy, and systemd unit. It does not install the managed ORC services themselves. The unit's working directory is the checkout from which the installer was run.

### Checkout permissions

A checkout under a private home directory may fail with `status=200/CHDIR` and `Changing to the requested working directory failed: Permission denied`. This means the service account cannot traverse the checkout path. Do not run the HTTP service as root to work around it.

For a checkout at `/home/markis/src/OpenRoadCode`, the following ACLs grant traversal of the parent directories and read/traverse access to the checkout. Adjust the path and account name for your installation. This is a development-host workaround; it grants read access to all readable repository contents, so do not use it on a checkout containing secrets or private data. A dedicated, root-owned deployment directory with only required runtime files is preferable for production.

```bash
sudo apt install acl
sudo setfacl -m u:openroadcode-service-manager:--x /home/markis
sudo setfacl -m u:openroadcode-service-manager:--x /home/markis/src
sudo setfacl -R -m u:openroadcode-service-manager:rX /home/markis/src/OpenRoadCode
sudo -u openroadcode-service-manager test -r /home/markis/src/OpenRoadCode/services/linux/systemd_service_manager_http.py && echo 'repo readable'
sudo systemctl restart openroadcode-service-manager
```

Existing ACLs are not automatically inherited by newly created files. Recheck access after checkout changes. The installer should eventually preflight this access before enabling the unit.

## Verify permissions and authentication

```bash
systemctl show openroadcode-service-manager -p User -p Group -p ExecStart
sudo visudo -cf /etc/sudoers.d/openroadcode-service-manager
sudo ls -l /etc/openroadcode/service-manager.env
curl -i http://127.0.0.1:8769/services
```

The unauthenticated request should return 401. Read the token without printing it:

```bash
TOKEN=$(sudo sed -n 's/^OPENROADCODE_SERVICE_MANAGER_TOKEN=//p' /etc/openroadcode/service-manager.env)
curl -i -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8769/services
```

Expect HTTP 200 and JSON containing the four service states. Missing units may report unknown or stopped; the manager does not create them. Do not paste the token into logs, screenshots, or issue reports. Clear the shell variable when finished with `unset TOKEN`.

## Android and VM test

Find the VM address with `hostname -I`. Verify the API is reachable at that address before configuring Android. For a NAT-only VM, use an explicit host port-forward and the host's reachable address; do not assume the guest's private NAT address is reachable from the phone. Keep the listener restricted to the intended network.

In the Android bridge, open OpenRoadCode Services, configure the Remote Pi target with `http://HOST:8769` and the bearer token, then select Remote Pi. The target can be a Linux VM. Verify status refresh and switching between Termux and Remote Pi before issuing service actions. Do not send the token to the Termux endpoint.

For write testing, first inspect installed units with `systemctl list-unit-files | grep -E 'openroadcode|readsb'`. Use only an existing service that is safe to interrupt. The API accepts POST `/services/<name>/start`, `/stop`, `/restart`, and `/stack/core/start` or `/stack/core/stop`. The manager has a fixed allowlist; arbitrary test-unit names are not supported. Do not create misleading aliases or replace production units just to exercise the API. Unit tests with a mocked manager are the appropriate way to test actions without affecting real services.

Check the journal after failures. A successful HTTP response proves the request was handled, not that every downstream ORC dependency is healthy. Verify the actual unit state separately. Avoid starting the core stack until the individual services and their dependencies are understood.

## Current limitations

The installer does not yet preflight checkout traversal, and the HTTP endpoint has no TLS. The service manager's sudo policy is deliberately limited to the approved units, but those units may themselves run privileged code. Review their unit files and dependencies before deployment. Keep the Linux branch separate until VM and Pi validation is complete.
