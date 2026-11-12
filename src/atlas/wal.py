
from __future__ import annotations

import os
import struct
import threading
import zlib
from pathlib import Path
from typing import Self


class WALCorruptionError(Exception):
    """Raised when a WAL record is corrupted."""


class WAL:
    """
    Append-only Write-Ahead Log.

    Record format:
        4 bytes: magic marker
        4 bytes: payload length
        4 bytes: CRC32 checksum
        N bytes: payload
    """

    MAGIC = b"ATX1"
    HEADER = struct.Struct(">4sII")
    MAX_RECORD_SIZE = 64 * 1024 * 1024  # 64 MB

    def __init__(self, file_path: str | Path, sync: bool = True):
        self.path = Path(file_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

        self.sync = sync
        self._lock = threading.RLock()
        self._file = self.path.open("a+b")

        # Repair incomplete final record during startup.
        try:
            self.read_all(repair=True)
        except Exception:
            self._file.close()
            raise

    def append(self, data: bytes) -> int:
        """Append one record and return its starting file offset."""
        if not isinstance(data, bytes):
            raise TypeError("WAL data must be bytes")

        if len(data) > self.MAX_RECORD_SIZE:
            raise ValueError("WAL record exceeds maximum size")

        checksum = zlib.crc32(data) & 0xFFFFFFFF
        header = self.HEADER.pack(self.MAGIC, len(data), checksum)

        with self._lock:
            self._file.seek(0, os.SEEK_END)
            offset = self._file.tell()

            self._file.write(header)
            self._file.write(data)
            self._file.flush()

            if self.sync:
                os.fsync(self._file.fileno())

            return offset

    def read_all(self, repair: bool = False) -> list[bytes]:
        """Read all valid records from the WAL."""
        with self._lock:
            self._file.flush()
            self._file.seek(0)

            records = []
            valid_end = 0

            while True:
                header = self._file.read(self.HEADER.size)

                if not header:
                    break

                if len(header) < self.HEADER.size:
                    if repair:
                        self._truncate(valid_end)
                        break
                    raise WALCorruptionError("Incomplete WAL header")

                magic, length, expected_crc = self.HEADER.unpack(header)

                if magic != self.MAGIC:
                    raise WALCorruptionError(
                        f"Invalid WAL magic at offset {valid_end}"
                    )

                if length > self.MAX_RECORD_SIZE:
                    raise WALCorruptionError(
                        f"Invalid record length at offset {valid_end}"
                    )

                payload = self._file.read(length)

                if len(payload) < length:
                    if repair:
                        self._truncate(valid_end)
                        break
                    raise WALCorruptionError("Incomplete WAL payload")

                actual_crc = zlib.crc32(payload) & 0xFFFFFFFF

                if actual_crc != expected_crc:
                    raise WALCorruptionError(
                        f"Checksum mismatch at offset {valid_end}"
                    )

                records.append(payload)
                valid_end += self.HEADER.size + length

            self._file.seek(0, os.SEEK_END)
            return records

    def _truncate(self, size: int) -> None:
        """Remove an incomplete tail from the WAL."""
        self._file.seek(size)
        self._file.truncate()
        self._file.flush()

        if self.sync:
            os.fsync(self._file.fileno())

    def reset(self) -> None:
        """Safely truncate the WAL after its records are persisted elsewhere."""
        with self._lock:
            if self._file.closed:
                raise RuntimeError("WAL is closed")

            self._file.seek(0)
            self._file.truncate(0)
            self._file.flush()

            if self.sync:
                os.fsync(self._file.fileno())

    def close(self) -> None:
        with self._lock:
            if not self._file.closed:
                self._file.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
