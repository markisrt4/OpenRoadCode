from dataclasses import dataclass


@dataclass(frozen=True)
class TextInputRequest:
    prompt: str
    initial_text: str = ""
    allow_empty: bool = False