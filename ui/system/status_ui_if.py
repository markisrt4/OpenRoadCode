"""! @brief Explicit UI contract and values for application status reporting."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto

from ui.ui_if import UiIf


class StatusSeverity(Enum):
    """! @brief Semantic importance of an application status."""

    INFORMATION = auto()
    SUCCESS = auto()
    WARNING = auto()
    ERROR = auto()


@dataclass(frozen=True, slots=True)
class StatusMessage:
    """! @brief Describe application status without prescribing presentation.

    @param summary Short human-readable status summary.
    @param severity Semantic importance of the status.
    @param detail Optional supporting detail.
    @param source Optional subsystem or component that produced the status.
    """

    summary: str
    severity: StatusSeverity = StatusSeverity.INFORMATION
    detail: str | None = None
    source: str | None = None


class StatusUiIf(UiIf, ABC):
    """! @brief Present semantic application status information.

    Implementations may use a bar, notification area, log, overlay, speech, or
    another suitable presentation. The contract does not prescribe color,
    placement, duration, queuing, or dismissal behavior.
    """

    @abstractmethod
    def set_status(self, status: StatusMessage | None) -> None:
        """! @brief Set or clear the current application status.

        @param status Status to present, or None to clear it.
        """
        ...
