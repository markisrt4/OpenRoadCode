from dataclasses import dataclass
from typing import Optional, Callable


StatusCallback = Optional[Callable[[str], None]]


@dataclass
class SDRResourceManager:
    """Coordinate advisory ownership of a shared SDR device."""
    current_owner: Optional[str] = None

    def acquire(
        self,
        owner: str,
        force: bool = True,
        set_status: StatusCallback = None,
    ) -> bool:
        """Acquire the SDR for an owner.

        @param owner Stable name of the requesting component.
        @param force Transfer ownership when another owner holds the SDR.
        @param set_status Optional status-message callback.
        @return Whether ownership was acquired.
        """
        if self.current_owner is None:
            self.current_owner = owner
            self._status(set_status, f"SDR acquired by {owner}")
            return True

        if self.current_owner == owner:
            return True

        if not force:
            self._status(
                set_status,
                f"SDR already in use by {self.current_owner}",
            )
            return False

        self._status(
            set_status,
            f"SDR ownership changed: {self.current_owner} → {owner}",
        )
        self.current_owner = owner
        return True

    def release(
        self,
        owner: str,
        set_status: StatusCallback = None,
    ) -> None:
        """Release the SDR when it is held by ``owner``."""
        if self.current_owner == owner:
            self.current_owner = None
            self._status(set_status, f"SDR released by {owner}")

    def is_owned_by(self, owner: str) -> bool:
        """Return whether ``owner`` currently holds the SDR."""
        return self.current_owner == owner

    def get_owner(self) -> Optional[str]:
        """Return the current owner name, or ``None`` when unowned."""
        return self.current_owner

    @staticmethod
    def _status(set_status: StatusCallback, message: str) -> None:
        if set_status:
            set_status(message)
