"""Real loopback setup HTTP with synthetic Android responses, never sends SMS."""
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlencode, urlsplit

from services.common.service_manager_sms_connect import SmsConnectionSessions
from services.common.service_manager_sms_credentials import connection_tokens, client_token_path, load_token
from services.termux.service_manager_http import ServiceManagerHandler

ANDROID = 'android-synthetic-' + 'x' * 32
CLIENT = 'client-synthetic-' + 'y' * 32


class AndroidResponse:
    status = 200
    def read(self, size):
        return b'{"read_sms_granted":true,"send_sms_granted":false,"send_supported":false}'
    def getheader(self, name):
        return None


class SmsConnectHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {'XDG_CONFIG_HOME': self.temp.name,
            'OPENROADCODE_SMS_TOKEN': CLIENT, 'OPENROADCODE_SMS_ENABLED': '0',
            'OPENROADCODE_ANDROID_SMS_TOKEN': 'stale-override'}, clear=True)
        self.env.start()
        class Handler(ServiceManagerHandler):
            sms_connections = SmsConnectionSessions()
        self.handler = Handler
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.android = patch('services.common.service_manager_sms_connect.HTTPConnection')
        self.connection = self.android.start()
        self.connection.return_value.getresponse.return_value = AndroidResponse()

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join()
        self.android.stop(); self.env.stop(); self.temp.cleanup()

    def request(self, method, path, body=None, bearer=None, form=None):
        headers = {'Host': 'untrusted.example.org'}
        if bearer:
            headers['Authorization'] = 'Bearer ' + bearer
        if form is not None:
            raw = urlencode(form).encode()
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        else:
            raw = json.dumps(body or {}).encode() if method == 'POST' else None
        client = HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
        try:
            client.request(method, path, raw, headers)
            response = client.getresponse()
            data = response.read()
            result = json.loads(data) if 'application/json' in response.getheader('Content-Type', '') else data.decode()
            return response.status, result, dict(response.getheaders())
        finally:
            client.close()

    def begin(self):
        status, session, _ = self.request('POST', '/sms/connect/start')
        self.assertEqual(status, 200)
        self.assertTrue(session['approval_url'].startswith('http://127.0.0.1:'))
        self.assertNotIn('untrusted', session['approval_url'])
        return session

    def approve(self, session, decision='approve'):
        url = urlsplit(session['approval_url'])
        approval = parse_qs(url.query)['token'][0]
        return self.request('POST', url.path, form={'approval_token': approval, 'decision': decision})

    def complete(self, session, token=ANDROID):
        return self.request('POST', '/sms/connect/complete/' + session['session_id'],
                            {'token': token}, session['poll_token'])

    def test_explicit_approval_verifies_gateway_saves_and_repairs_without_restart(self):
        session = self.begin()
        self.assertEqual(self.approve(session)[0], 200)
        code, body, _ = self.complete(session)
        self.assertEqual((code, body), (200, {'status': 'connected'}))
        self.connection.assert_called_once_with('127.0.0.1', 8773, timeout=3)
        self.connection.return_value.request.assert_called_once_with(
            'GET', '/sms/capabilities', headers={'Authorization': 'Bearer ' + ANDROID})
        self.assertEqual(connection_tokens(), (True, CLIENT, ANDROID))
        self.assertEqual(client_token_path().stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.complete(session)[0], 409)
        self.assertEqual(self.connection.call_count, 1)
        # Actual SMS proxy now uses the saved Android credential, ignoring stale env.
        with patch('services.common.service_manager_sms_proxy.HTTPConnection') as proxy:
            proxy.return_value.getresponse.return_value = AndroidResponse()
            self.assertEqual(self.request('GET', '/sms/capabilities', bearer=CLIENT)[0], 200)
            self.assertEqual(proxy.return_value.request.call_args.kwargs['headers']['Authorization'], 'Bearer ' + ANDROID)

    def test_no_approval_or_pairing_token_cannot_provision(self):
        session = self.begin()
        self.assertEqual(self.complete(session)[0], 409)
        self.assertEqual(self.request('POST', '/sms/connect/complete/' + session['session_id'],
                         {'token': ANDROID}, 'ordinary-paired-token')[0], 401)
        self.connection.assert_not_called()
        self.assertIsNone(load_token())

    def test_wrong_android_credential_cannot_replace_existing_credential(self):
        from services.common.service_manager_sms_credentials import save_token
        save_token(ANDROID)
        session = self.begin(); self.approve(session)
        self.connection.return_value.getresponse.return_value.status = 401
        self.assertEqual(self.complete(session, 'invalid-' + 'z' * 32)[0], 502)
        self.assertEqual(load_token(), ANDROID)
        self.assertIsNone(load_token(client_token_path()))

    def test_denial_cancel_and_expiry_cannot_complete(self):
        denied = self.begin(); self.approve(denied, 'deny')
        self.assertEqual(self.complete(denied)[0], 409)
        cancelled = self.begin()
        self.assertEqual(self.request('POST', '/sms/connect/cancel/' + cancelled['session_id'],
                         {}, cancelled['poll_token'])[0], 200)
        self.assertEqual(self.complete(cancelled)[0], 409)
        expired = self.begin()
        with patch('services.common.service_manager_browser_pairing.time.time', return_value=time.time() + 200):
            self.assertEqual(self.complete(expired)[0], 410)
        self.connection.assert_not_called()

    def test_browser_approval_requires_capability_and_is_not_cacheable(self):
        session = self.begin()
        url = urlsplit(session['approval_url'])
        status, page, headers = self.request('GET', url.path + '?' + url.query)
        self.assertEqual(status, 200)
        self.assertIn('No message will be sent', page)
        self.assertNotIn(ANDROID, page); self.assertNotIn(CLIENT, page)
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertEqual(headers['Referrer-Policy'], 'no-referrer')
        self.assertEqual(self.request('POST', url.path, form={'decision': 'approve', 'approval_token': 'wrong'})[0], 401)

    def test_non_loopback_is_rejected_even_with_valid_capability(self):
        from services.common.service_manager_sms_connect import serve_sms_connect
        class Remote:
            path = '/sms/connect/start'
            client_address = ('192.0.2.1', 123)
            def _json(self, status, payload): self.status = status
        remote = Remote()
        self.assertTrue(serve_sms_connect(remote, 'POST'))
        self.assertEqual(remote.status, 403)

    def test_sessions_are_bounded_and_storage_failures_remain_retryable(self):
        session = self.begin(); self.approve(session)
        with patch('services.common.service_manager_sms_connect.save_token', side_effect=OSError('private detail')):
            status, body, _ = self.complete(session)
            self.assertEqual(status, 500)
            self.assertNotIn('private detail', str(body))
        self.assertEqual(self.complete(session)[0], 200)
        for _ in range(15): self.begin()
        self.assertEqual(self.request('POST', '/sms/connect/start')[0], 429)
