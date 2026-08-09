from __future__ import annotations

from collections.abc import Iterator, Mapping

from apps.carUi.runtime.car_ui_runtime import RadioRuntime


class RadioRuntimeRegistry:
    """Read-only registry of configured radio runtimes."""

    def __init__(self, runtimes: Mapping[str, RadioRuntime]) -> None:
        self._runtimes = dict(runtimes)

    def get(self, key: str) -> RadioRuntime:
        try:
            return self._runtimes[key]
        except KeyError as exc:
            available = ", ".join(sorted(self._runtimes)) or "<none>"
            raise KeyError(
                f"Unknown radio runtime '{key}'. Available: {available}"
            ) from exc

    def keys(self) -> tuple[str, ...]:
        return tuple(self._runtimes.keys())

    def values(self) -> tuple[RadioRuntime, ...]:
        return tuple(self._runtimes.values())

    def items(self) -> tuple[tuple[str, RadioRuntime], ...]:
        return tuple(self._runtimes.items())

    def __contains__(self, key: object) -> bool:
        return key in self._runtimes

    def __len__(self) -> int:
        return len(self._runtimes)

    def __iter__(self) -> Iterator[str]:
        return iter(self._runtimes)
