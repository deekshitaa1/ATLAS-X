
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Self

from atlas.wal import WAL


class StorageCorruptionError(Exception):
    """Raised when stored database records cannot be recovered."""


class StorageEngine:
    """
    Persistent key-value storage engine.

    Every write is recorded in the WAL before memory is updated.
    On startup, the in-memory index is rebuilt from the WAL.
    """

    def __init__(self, data_dir: str | Path, sync: bool = True):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self._lock = threading.RLock()
        self._data: dict[str, Any] = {}
        self._closed = False

        self.wal = WAL(self.data_dir / "atlas.wal", sync=sync)

        try:
            self._recover()
        except Exception:
            self.wal.close()
            self._closed = True
            raise

    @staticmethod
    def _validate_key(key: str) -> None:
        if not isinstance(key, str):
            raise TypeError("Key must be a string")

        if not key:
            raise ValueError("Key cannot be empty")

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("StorageEngine is closed")

    def _recover(self) -> None:
        """Rebuild the in-memory index by replaying WAL records."""
        records = self.wal.read_all()

        for record in records:
            try:
                operation = json.loads(record.decode("utf-8"))

                if not isinstance(operation, dict):
                    raise TypeError("Record must be a JSON object")

                op = operation.get("op")
                key = operation.get("key")

                self._validate_key(key)

                if op == "put":
                    if "value" not in operation:
                        raise ValueError("PUT record has no value")

                    self._data[key] = operation["value"]

                elif op == "delete":
                    self._data.pop(key, None)

                else:
                    raise ValueError(f"Unknown operation: {op}")

            except (
                UnicodeDecodeError,
                json.JSONDecodeError,
                TypeError,
                ValueError,
            ) as exc:
                raise StorageCorruptionError(
                    "Unable to recover a WAL record"
                ) from exc

    def put(self, key: str, value: Any) -> None:
        """Persist a key-value pair."""
        self._validate_key(key)

        record = json.dumps(
            {"op": "put", "key": key, "value": value},
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")

        with self._lock:
            self._ensure_open()

            self.wal.append(record)
            self._data[key] = value

    def get(self, key: str) -> Any | None:
        """Return the value for a key, or None if it does not exist."""
        self._validate_key(key)

        with self._lock:
            self._ensure_open()
            return self._data.get(key)

    def exists(self, key: str) -> bool:
        """Check whether a key exists."""
        self._validate_key(key)

        with self._lock:
            self._ensure_open()
            return key in self._data

    def delete(self, key: str) -> bool:
        """Delete a key. Return True if it existed."""
        self._validate_key(key)

        record = json.dumps(
            {"op": "delete", "key": key},
            separators=(",", ":"),
        ).encode("utf-8")

        with self._lock:
            self._ensure_open()

            existed = key in self._data

            self.wal.append(record)
            self._data.pop(key, None)

            return existed

    def scan(self, prefix: str = "") -> dict[str, Any]:
        """Return all key-value pairs matching a prefix."""
        if not isinstance(prefix, str):
            raise TypeError("Prefix must be a string")

        with self._lock:
            self._ensure_open()

            return {
                key: self._data[key]
                for key in sorted(self._data)
                if key.startswith(prefix)
            }

    def count(self) -> int:
        """Return the number of stored keys."""
        with self._lock:
            self._ensure_open()
            return len(self._data)

    def close(self) -> None:
        with self._lock:
            if not self._closed:
                self.wal.close()
                self._closed = True

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
