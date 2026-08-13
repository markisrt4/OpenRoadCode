"""Unit tests for RemoteTextInputDevice."""

import pytest

from controllers.text_input import RemoteTextInputDevice, TextInputRequest


def test_submit_completes_active_request() -> None:
    received: list[str] = []
    device = RemoteTextInputDevice()

    device.request_text(TextInputRequest("Destination"), received.append)
    device.submit("  Henry Ford Museum  ")

    assert received == ["Henry Ford Museum"]
    assert device.is_active is False
    assert device.request is None


def test_request_exposes_prompt_and_initial_text() -> None:
    device = RemoteTextInputDevice()
    request = TextInputRequest("Destination", initial_text="Detroit")

    device.request_text(request, lambda _text: None)

    assert device.request == request


def test_second_request_while_active_is_rejected() -> None:
    device = RemoteTextInputDevice()
    device.request_text(TextInputRequest("First"), lambda _text: None)

    with pytest.raises(RuntimeError):
        device.request_text(TextInputRequest("Second"), lambda _text: None)


def test_submit_without_active_request_is_rejected() -> None:
    device = RemoteTextInputDevice()

    with pytest.raises(RuntimeError):
        device.submit("Detroit")


def test_empty_text_is_rejected_by_default() -> None:
    device = RemoteTextInputDevice()
    device.request_text(TextInputRequest("Destination"), lambda _text: None)

    with pytest.raises(ValueError):
        device.submit("   ")

    assert device.is_active is True


def test_empty_text_can_be_allowed() -> None:
    received: list[str] = []
    device = RemoteTextInputDevice()
    device.request_text(
        TextInputRequest("Optional note", allow_empty=True),
        received.append,
    )

    device.submit("   ")

    assert received == [""]
    assert device.is_active is False


def test_cancel_invokes_callback_and_clears_request() -> None:
    cancelled: list[bool] = []
    device = RemoteTextInputDevice()
    device.request_text(
        TextInputRequest("Destination"),
        lambda _text: None,
        lambda: cancelled.append(True),
    )

    device.cancel()

    assert cancelled == [True]
    assert device.is_active is False
    assert device.request is None


def test_cancel_without_request_is_noop() -> None:
    device = RemoteTextInputDevice()

    device.cancel()

    assert device.is_active is False
