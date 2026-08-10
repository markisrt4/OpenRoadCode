from __future__ import annotations

from abc import ABC, abstractmethod


class SecretManagerIf(ABC):
    """Retrieve secrets without exposing their storage mechanism."""

    @abstractmethod
    def get_secret(self, name: str) -> str | None:
        """Return a secret value, or ``None`` when it is unavailable.

        @param name Stable secret name.
        @return Secret value, or `None` when it is unavailable.
        """

    def require_secret(self, name: str) -> str:
        """Return a required secret or raise a descriptive error.

        @param name Stable secret name.
        @return Required secret value.
        @exception RuntimeError if the secret is unavailable.
        """
        value = self.get_secret(name)

        if value is None:
            raise RuntimeError(
                f"Required secret is unavailable: {name}"
            )

        return value
