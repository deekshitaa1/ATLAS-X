from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Self


@dataclass(frozen=True, slots=True)
class Version:
    sequence: int
    value: Any
    deleted: bool = False


class MVCCStore:
    """In-memory MVCC store with snapshot transactions."""

    def __init__(self) -> None:
        self._versions: dict[str, list[Version]] = {}
        self._sequence = 0
        self._lock = threading.RLock()

    @property
    def sequence(self) -> int:
        with self._lock:
            return self._sequence

    def snapshot(self) -> int:
        with self._lock:
            return self._sequence

    def begin(self) -> MVCCTransaction:
        with self._lock:
            return MVCCTransaction(self, self._sequence)

    def put(self, key: str, value: Any) -> int:
        self._validate_key(key)
        with self._lock:
            self._sequence += 1
            self._versions.setdefault(key, []).append(
                Version(self._sequence, value)
            )
            return self._sequence

    def delete(self, key: str) -> int:
        self._validate_key(key)
        with self._lock:
            self._sequence += 1
            self._versions.setdefault(key, []).append(
                Version(self._sequence, None, deleted=True)
            )
            return self._sequence

    def get(self, key: str, snapshot: int | None = None) -> Any | None:
        self._validate_key(key)
        with self._lock:
            if snapshot is None:
                snapshot = self._sequence
            self._validate_snapshot(snapshot)
            version = self._visible_version(key, snapshot)
            if version is None or version.deleted:
                return None
            return version.value

    def contains(self, key: str, snapshot: int | None = None) -> bool:
        self._validate_key(key)
        with self._lock:
            if snapshot is None:
                snapshot = self._sequence
            self._validate_snapshot(snapshot)
            version = self._visible_version(key, snapshot)
            return version is not None and not version.deleted

    def scan(self, snapshot: int | None = None) -> dict[str, Any]:
        with self._lock:
            if snapshot is None:
                snapshot = self._sequence
            self._validate_snapshot(snapshot)
            result = {}
            for key in sorted(self._versions):
                version = self._visible_version(key, snapshot)
                if version is not None and not version.deleted:
                    result[key] = version.value
            return result

    def _commit(
        self,
        snapshot: int,
        operations: dict[str, tuple[str, Any]],
    ) -> None:
        with self._lock:
            for key in operations:
                latest = self._visible_version(key, self._sequence)
                if latest is not None and latest.sequence > snapshot:
                    raise RuntimeError(f"Write conflict on key: {key}")

            for key, (action, value) in operations.items():
                self._sequence += 1
                self._versions.setdefault(key, []).append(
                    Version(
                        self._sequence,
                        value,
                        deleted=(action == "delete"),
                    )
                )

    def _visible_version(self, key: str, snapshot: int) -> Version | None:
        for version in reversed(self._versions.get(key, [])):
            if version.sequence <= snapshot:
                return version
        return None

    def _validate_snapshot(self, snapshot: int) -> None:
        if not isinstance(snapshot, int) or isinstance(snapshot, bool):
            raise TypeError("snapshot must be an integer")
        if snapshot < 0 or snapshot > self._sequence:
            raise ValueError("Invalid snapshot sequence")

    @staticmethod
    def _validate_key(key: str) -> None:
        if not isinstance(key, str):
            raise TypeError("Key must be a string")
        if not key:
            raise ValueError("Key cannot be empty")


class MVCCTransaction:
    """Snapshot transaction with staged writes and conflict detection."""

    def __init__(self, store: MVCCStore, snapshot: int) -> None:
        self._store = store
        self.snapshot = snapshot
        self._operations: dict[str, tuple[str, Any]] = {}
        self._active = True

    def _ensure_active(self) -> None:
        if not self._active:
            raise RuntimeError("Transaction is no longer active")

    def get(self, key: str) -> Any | None:
        self._ensure_active()
        self._store._validate_key(key)
        if key in self._operations:
            action, value = self._operations[key]
            return None if action == "delete" else value
        return self._store.get(key, self.snapshot)

    def put(self, key: str, value: Any) -> None:
        self._ensure_active()
        self._store._validate_key(key)
        self._operations[key] = ("put", value)

    def delete(self, key: str) -> None:
        self._ensure_active()
        self._store._validate_key(key)
        self._operations[key] = ("delete", None)

    def commit(self) -> None:
        self._ensure_active()
        self._store._commit(self.snapshot, self._operations)
        self._active = False

    def rollback(self) -> None:
        self._ensure_active()
        self._operations.clear()
        self._active = False

    def __enter__(self) -> Self:
        self._ensure_active()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
