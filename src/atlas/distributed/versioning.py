from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class VersionedValue:
    version: int
    value: Any

    def __post_init__(self) -> None:
        if not isinstance(self.version, int) or isinstance(self.version, bool):
            raise TypeError("version must be an integer")
        if self.version < 1:
            raise ValueError("version must be positive")


class VersionClock:
    """Generate monotonically increasing versions safely."""

    def __init__(self) -> None:
        self._version = 0

    def next_version(self) -> int:
        self._version += 1
        return self._version

    def observe(self, version: int) -> None:
        if not isinstance(version, int) or isinstance(version, bool):
            raise TypeError("version must be an integer")
        if version < 0:
            raise ValueError("version cannot be negative")
        self._version = max(self._version, version)

    @property
    def current(self) -> int:
        return self._version
