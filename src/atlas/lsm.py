from __future__ import annotations

import json
import threading
from pathlib import Path
from types import TracebackType
from typing import Any, ClassVar, Self

from atlas.bloom import BloomFilter
from atlas.transaction import Transaction
from atlas.wal import WAL

_NOT_FOUND = object()


class LSMCorruptionError(Exception):
    """Raised when LSM storage records cannot be recovered."""


class LSMTree:
    """
    WAL-backed educational Log-Structured Merge Tree.

    Features:
    - Write-Ahead Logging
    - MemTable
    - Immutable sorted SSTables
    - Bloom filters
    - Tombstones
    - Prefix scans
    - Basic compaction
    - WAL checkpoint recovery
    """

    TOMBSTONE: ClassVar[dict[str, bool]] = {
        "__atlas_deleted__": True
    }

    def __init__(
        self,
        data_dir: str | Path,
        memtable_limit: int = 100,
        bloom_capacity: int = 1000,
        sync: bool = True,
    ) -> None:
        if not isinstance(memtable_limit, int) or isinstance(memtable_limit, bool):
            raise TypeError("memtable_limit must be an integer")

        if memtable_limit <= 0:
            raise ValueError("memtable_limit must be positive")

        if not isinstance(bloom_capacity, int) or isinstance(bloom_capacity, bool):
            raise TypeError("bloom_capacity must be an integer")

        if bloom_capacity <= 0:
            raise ValueError("bloom_capacity must be positive")

        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.memtable_limit = memtable_limit
        self.bloom_capacity = bloom_capacity

        self._memtable: dict[str, Any] = {}
        self._tables: list[tuple[Path, BloomFilter]] = []
        self._lock = threading.RLock()
        self._closed = False

        self._load_tables()

        self._wal = WAL(self.data_dir / "atlas.wal", sync=sync)

        try:
            self._recover_wal()
        except Exception:
            self._wal.close()
            self._closed = True
            raise

    @staticmethod
    def _validate_key(key: str) -> None:
        if not isinstance(key, str):
            raise TypeError("Key must be a string")

        if not key:
            raise ValueError("Key cannot be empty")

    @staticmethod
    def _is_tombstone(value: Any) -> bool:
        return (
            isinstance(value, dict)
            and value == LSMTree.TOMBSTONE
        )

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("LSMTree is closed")

    def _table_paths(self) -> list[Path]:
        try:
            return sorted(
                self.data_dir.glob("*.sst"),
                key=lambda path: int(path.stem),
                reverse=True,
            )
        except ValueError as exc:
            raise LSMCorruptionError(
                "Invalid SSTable filename"
            ) from exc

    def _load_tables(self) -> None:
        for path in self._table_paths():
            bloom = BloomFilter(capacity=self.bloom_capacity)

            try:
                with path.open("r", encoding="utf-8") as file:
                    for line in file:
                        if not line.strip():
                            continue

                        record = json.loads(line)
                        key = record["key"]
                        self._validate_key(key)
                        bloom.add(key)

            except (OSError, ValueError, KeyError, TypeError) as exc:
                raise LSMCorruptionError(
                    f"Unable to load SSTable: {path.name}"
                ) from exc

            self._tables.append((path, bloom))

    def _recover_wal(self) -> None:
        """Replay WAL records written after the latest checkpoint."""
        records = self._wal.read_all()

        checkpoint_index = -1

        for index, raw_record in enumerate(records):
            try:
                record = json.loads(raw_record.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise LSMCorruptionError(
                    "Invalid JSON in WAL"
                ) from exc

            if isinstance(record, dict) and record.get("op") == "checkpoint":
                checkpoint_index = index

        for raw_record in records[checkpoint_index + 1:]:
            try:
                record = json.loads(raw_record.decode("utf-8"))

                if not isinstance(record, dict):
                    raise TypeError("WAL record must be an object")

                operation = record.get("op")

                if operation == "put":
                    key = record.get("key")
                    self._validate_key(key)

                    if "value" not in record:
                        raise ValueError("PUT record has no value")

                    self._memtable[key] = record["value"]

                elif operation == "delete":
                    key = record.get("key")
                    self._validate_key(key)
                    self._memtable[key] = self.TOMBSTONE.copy()

                elif operation == "batch":
                    operations = record.get("operations")

                    if not isinstance(operations, list):
                        raise ValueError("Invalid WAL batch")

                    for item in operations:
                        if not isinstance(item, dict):
                            raise TypeError("Invalid batch item")

                        action = item.get("op")
                        key = item.get("key")
                        self._validate_key(key)

                        if action == "put" and "value" in item:
                            self._memtable[key] = item["value"]
                        elif action == "delete":
                            self._memtable[key] = self.TOMBSTONE.copy()
                        else:
                            raise ValueError("Invalid batch operation")

                elif operation == "checkpoint":
                    continue

                else:
                    raise ValueError("Unknown WAL operation")

            except (
                UnicodeDecodeError,
                json.JSONDecodeError,
                TypeError,
                ValueError,
            ) as exc:
                raise LSMCorruptionError(
                    "Unable to recover WAL record"
                ) from exc

    def _append_wal(self, record: dict[str, Any]) -> None:
        payload = json.dumps(
            record,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")

        self._wal.append(payload)

    def put(self, key: str, value: Any) -> None:
        self._validate_key(key)

        # Validate serialization before writing to WAL.
        json.dumps(value, allow_nan=False)

        with self._lock:
            self._ensure_open()

            self._append_wal({
                "op": "put",
                "key": key,
                "value": value,
            })

            self._memtable[key] = value

            if len(self._memtable) >= self.memtable_limit:
                self.flush()

    def delete(self, key: str) -> None:
        self._validate_key(key)

        with self._lock:
            self._ensure_open()

            self._append_wal({
                "op": "delete",
                "key": key,
            })

            self._memtable[key] = self.TOMBSTONE.copy()

            if len(self._memtable) >= self.memtable_limit:
                self.flush()

    def _search_table(self, path: Path, key: str) -> Any:
        with path.open("r", encoding="utf-8") as file:
            for line in file:
                if not line.strip():
                    continue

                record = json.loads(line)
                current_key = record["key"]

                if current_key == key:
                    return record["value"]

                if current_key > key:
                    break

        return _NOT_FOUND

    def _lookup(self, key: str) -> Any:
        if key in self._memtable:
            return self._memtable[key]

        for path, bloom in self._tables:
            if not bloom.might_contain(key):
                continue

            value = self._search_table(path, key)

            if value is not _NOT_FOUND:
                return value

        return _NOT_FOUND

    def get(self, key: str) -> Any | None:
        self._validate_key(key)

        with self._lock:
            self._ensure_open()

            value = self._lookup(key)

            if value is _NOT_FOUND or self._is_tombstone(value):
                return None

            return value

    def contains(self, key: str) -> bool:
        self._validate_key(key)

        with self._lock:
            self._ensure_open()

            value = self._lookup(key)
            return value is not _NOT_FOUND and not self._is_tombstone(value)

    def scan(self, prefix: str = "") -> dict[str, Any]:
        if not isinstance(prefix, str):
            raise TypeError("Prefix must be a string")

        with self._lock:
            self._ensure_open()

            keys = set(self._memtable)

            for path, _ in self._tables:
                with path.open("r", encoding="utf-8") as file:
                    for line in file:
                        if line.strip():
                            keys.add(json.loads(line)["key"])

            result = {}

            for key in sorted(keys):
                if not key.startswith(prefix):
                    continue

                value = self._lookup(key)

                if value is not _NOT_FOUND and not self._is_tombstone(value):
                    result[key] = value

            return result

    def _write_sstable(
        self,
        records: dict[str, Any],
        table_id: int,
    ) -> tuple[Path, BloomFilter]:
        final_path = self.data_dir / f"{table_id:020d}.sst"
        temporary_path = final_path.with_suffix(".tmp")

        bloom = BloomFilter(
            capacity=max(self.bloom_capacity, len(records), 1)
        )

        try:
            with temporary_path.open("w", encoding="utf-8") as file:
                for key in sorted(records):
                    record = {
                        "key": key,
                        "value": records[key],
                    }

                    file.write(
                        json.dumps(
                            record,
                            separators=(",", ":"),
                            ensure_ascii=False,
                            allow_nan=False,
                        ) + "\n"
                    )

                    bloom.add(key)

                file.flush()
                import os
                os.fsync(file.fileno())

            temporary_path.replace(final_path)

        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise

        return final_path, bloom

    def _next_table_id(self) -> int:
        existing = [
            int(path.stem)
            for path in self.data_dir.glob("*.sst")
        ]

        return max(existing, default=0) + 1

    def _checkpoint(self) -> None:
        self._append_wal({"op": "checkpoint"})

    def flush(self) -> Path | None:
        """Publish MemTable as an SSTable before checkpointing WAL."""
        with self._lock:
            self._ensure_open()

            if not self._memtable:
                return None

            table_id = self._next_table_id()

            final_path, bloom = self._write_sstable(
                self._memtable,
                table_id,
            )

            # The SSTable is durable before this checkpoint is appended.
            self._checkpoint()

            self._tables.insert(0, (final_path, bloom))
            self._memtable.clear()

            # All current MemTable records are now persisted in the SSTable.
            self._wal.reset()

            return final_path

    def compact(self) -> Path | None:
        """Merge SSTables and MemTable into one new SSTable."""
        with self._lock:
            self._ensure_open()

            if not self._tables:
                return self.flush()

            merged: dict[str, Any] = {}

            # Process oldest to newest.
            for path, _ in reversed(self._tables):
                with path.open("r", encoding="utf-8") as file:
                    for line in file:
                        if line.strip():
                            record = json.loads(line)
                            merged[record["key"]] = record["value"]

            # MemTable has the newest values.
            merged.update(self._memtable)

            compacted = {
                key: value
                for key, value in merged.items()
                if not self._is_tombstone(value)
            }

            final_path, bloom = self._write_sstable(
                compacted,
                self._next_table_id(),
            )

            # Publish the compacted table before checkpointing.
            self._checkpoint()

            old_tables = list(self._tables)

            self._tables = [(final_path, bloom)]
            self._memtable.clear()

            # Delete old files only after publishing and checkpointing.
            for old_path, _ in old_tables:
                old_path.unlink(missing_ok=True)

            # The compacted SSTable now contains all live records.
            self._wal.reset()

            return final_path

    def batch(self, operations: list[tuple]) -> None:
        """Apply multiple PUT and DELETE operations as one atomic batch."""
        with self._lock:
            self._ensure_open()

            if not isinstance(operations, list):
                raise TypeError("operations must be a list")

            prepared = []

            for operation in operations:
                if not isinstance(operation, tuple) or len(operation) not in (2, 3):
                    raise ValueError("Invalid batch operation")

                action = operation[0]

                if action == "put" and len(operation) == 3:
                    _, key, value = operation
                    self._validate_key(key)
                    json.dumps(value, allow_nan=False)
                    prepared.append({
                        "op": "put",
                        "key": key,
                        "value": value,
                    })

                elif action == "delete" and len(operation) == 2:
                    _, key = operation
                    self._validate_key(key)
                    prepared.append({
                        "op": "delete",
                        "key": key,
                    })

                else:
                    raise ValueError("Unsupported batch operation")

            if not prepared:
                return

            self._append_wal({
                "op": "batch",
                "operations": prepared,
            })

            for item in prepared:
                if item["op"] == "put":
                    self._memtable[item["key"]] = item["value"]
                else:
                    self._memtable[item["key"]] = self.TOMBSTONE.copy()

            if len(self._memtable) >= self.memtable_limit:
                self.flush()

    def transaction(self) -> Transaction:
        """Create a new transaction context."""
        with self._lock:
            self._ensure_open()
            return Transaction(self)

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return

            self.flush()
            self._wal.close()
            self._closed = True

    def __enter__(self) -> Self:
        self._ensure_open()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
