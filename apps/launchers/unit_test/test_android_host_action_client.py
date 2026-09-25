from __future__ import annotations

from unittest.mock import Mock, patch

from apps.launchers.android_host_action_client import (
    AndroidHostActionClient,
    AndroidHostActionClientError,
)


@patch("apps.launchers.android_host_action_client.urllib.request.urlopen")
def test_launch_package_posts_to_bridge(urlopen) -> None:
    response = Mock()
    response.status = 200
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    urlopen.return_value = response

    AndroidHostActionClient().launch_package("com.panera.bread")

    request = urlopen.call_args.args[0]
    assert request.full_url == "http://127.0.0.1:8770/launch/package"
    assert request.data == b"package=com.panera.bread"


def test_package_failure_falls_back_to_uri() -> None:
    client = AndroidHostActionClient()
    client.launch_package = Mock(side_effect=AndroidHostActionClientError("missing"))
    client.open_uri = Mock()

    result = client.open_package_or_uri("com.panera.bread", "https://example.com/order")

    assert result == "uri"
    client.open_uri.assert_called_once_with("https://example.com/order")
