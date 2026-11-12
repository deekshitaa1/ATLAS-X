
from __future__ import annotations

from typing import Any


class HashIndex:
    """In-memory hash index for exact key lookups."""

    def __init__(self):
        self._index: dict[str, Any] = {}

    def insert(self, key: str, value: Any) -> None:
        self._validate_key(key)
        self._index[key] = value

    def search(self, key: str) -> Any | None:
        self._validate_key(key)
        return self._index.get(key)

    def delete(self, key: str) -> bool:
        self._validate_key(key)

        if key not in self._index:
            return False

        del self._index[key]
        return True

    def contains(self, key: str) -> bool:
        self._validate_key(key)
        return key in self._index

    def scan(self) -> dict[str, Any]:
        return dict(self._index)

    def __len__(self) -> int:
        return len(self._index)

    @staticmethod
    def _validate_key(key: str) -> None:
        if not isinstance(key, str):
            raise TypeError("Key must be a string")

        if not key:
            raise ValueError("Key cannot be empty")
