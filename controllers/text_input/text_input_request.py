"""Request model for user-entered text."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TextInputRequest:
    """Describe one request for text input from a user."""

    prompt: str
    initial_text: str = ""
    allow_empty: bool = False
