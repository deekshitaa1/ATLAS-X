from __future__ import annotations

import json
from pathlib import Path
from types import TracebackType
from typing import Any, Self

from atlas.mvcc import MVCCStore
from atlas.wal import WALCorruptionError


class MVCCCorruptionError(Exception):
    """Raised when persistent MVCC data cannot be recovered."""


class PersistentMVCCStore(MVCCStore):
    """WAL-backed MVCC store with atomic transaction commits."""

    def __init__(self, data_dir: str | Path, sync: bool = True) -> None:
        from atlas.wal import WAL

        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        super().__init__()
        self._closed = False

        try:
            self._wal = WAL(self.data_dir / "mvcc.wal", sync=sync)
            self._recover()
        except WALCorruptionError as exc:
            self._closed = True
            raise MVCCCorruptionError("Corrupted MVCC WAL") from exc
        except Exception:
            if hasattr(self, "_wal"):
                self._wal.close()
            self._closed = True
            raise

    def _ensure_persistent_open(self) -> None:
        if self._closed:
            raise RuntimeError("PersistentMVCCStore is closed")

    def _append_record(self, record: dict[str, Any]) -> None:
        payload = json.dumps(
            record,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        self._wal.append(payload)

    def _recover(self) -> None:
        try:
            records = self._wal.read_all(repair=True)
            for raw in records:
                record = json.loads(raw.decode("utf-8"))
                if not isinstance(record, dict):
                    raise TypeError("WAL record must be an object")

                operation = record.get("op")

                if operation == "put":
                    super().put(record["key"], record["value"])
                elif operation == "delete":
                    super().delete(record["key"])
                elif operation == "batch":
                    operations = record["operations"]
                    if not isinstance(operations, list):
                        raise ValueError("Invalid batch")
                    for item in operations:
                        if not isinstance(item, dict):
                            raise TypeError("Invalid batch item")
                        action = item.get("op")
                        key = item.get("key")
                        if action == "put" and "value" in item:
                            super().put(key, item["value"])
                        elif action == "delete":
                            super().delete(key)
                        else:
                            raise ValueError("Invalid batch operation")
                else:
                    raise ValueError("Unknown MVCC WAL operation")

        except Exception as exc:
            raise MVCCCorruptionError("Unable to recover MVCC WAL") from exc

    def put(self, key: str, value: Any) -> int:
        self._validate_key(key)
        with self._lock:
            self._ensure_persistent_open()
            self._append_record({"op": "put", "key": key, "value": value})
            return super().put(key, value)

    def delete(self, key: str) -> int:
        self._validate_key(key)
        with self._lock:
            self._ensure_persistent_open()
            self._append_record({"op": "delete", "key": key})
            return super().delete(key)

    def begin(self):
        with self._lock:
            self._ensure_persistent_open()
            return super().begin()

    def _commit(self, snapshot: int, operations: dict[str, tuple[str, Any]]) -> None:
        with self._lock:
            self._ensure_persistent_open()

            for key in operations:
                latest = self._visible_version(key, self._sequence)
                if latest is not None and latest.sequence > snapshot:
                    raise RuntimeError(f"Write conflict on key: {key}")

            if not operations:
                return

            prepared = []
            for key, (action, value) in operations.items():
                self._validate_key(key)
                if action == "put":
                    prepared.append({"op": "put", "key": key, "value": value})
                elif action == "delete":
                    prepared.append({"op": "delete", "key": key})
                else:
                    raise ValueError("Invalid transaction operation")

            self._append_record({"op": "batch", "operations": prepared})
            super()._commit(snapshot, operations)

    def read_entry(self, key: str) -> tuple[bool, Any]:
        self._validate_key(key)
        with self._lock:
            self._ensure_persistent_open()
            version = self._visible_version(key, self._sequence)
            if version is None or version.deleted:
                return False, None
            return True, version.value

    def delete_existing(self, key: str) -> bool:
        self._validate_key(key)
        with self._lock:
            self._ensure_persistent_open()
            version = self._visible_version(key, self._sequence)
            if version is None or version.deleted:
                return False
            self._append_record({"op": "delete", "key": key})
            super().delete(key)
            return True

    def scan_prefix(self, prefix: str = "") -> dict[str, Any]:
        if not isinstance(prefix, str):
            raise TypeError("prefix must be a string")
        with self._lock:
            self._ensure_persistent_open()
            return {
                key: value
                for key, value in self.scan().items()
                if key.startswith(prefix)
            }

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._wal.close()
            self._closed = True

    def __enter__(self) -> Self:
        self._ensure_persistent_open()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
