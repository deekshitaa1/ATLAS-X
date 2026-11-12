
import pytest

from atlas.wal import WAL, WALCorruptionError


def test_append_and_read_multiple_records(tmp_path):
    path = tmp_path / "database.wal"

    with WAL(path) as wal:
        wal.append(b"first")
        wal.append(b"second")
        wal.append(b"third")

        assert wal.read_all() == [
            b"first",
            b"second",
            b"third",
        ]


def test_records_survive_reopen(tmp_path):
    path = tmp_path / "database.wal"

    with WAL(path) as wal:
        wal.append(b"persistent-data")

    with WAL(path) as wal:
        assert wal.read_all() == [b"persistent-data"]


def test_incomplete_tail_is_repaired(tmp_path):
    path = tmp_path / "database.wal"

    with WAL(path) as wal:
        wal.append(b"valid-record")

    with open(path, "ab") as file:
        file.write(b"ATX")

    with WAL(path) as wal:
        assert wal.read_all() == [b"valid-record"]


def test_checksum_corruption_is_detected(tmp_path):
    path = tmp_path / "database.wal"

    with WAL(path) as wal:
        wal.append(b"important-data")

    with open(path, "r+b") as file:
        file.seek(WAL.HEADER.size)
        file.write(b"X")

    with pytest.raises(WALCorruptionError):
        WAL(path)


def test_append_rejects_non_bytes(tmp_path):
    with WAL(tmp_path / "database.wal") as wal, pytest.raises(TypeError):
        wal.append("not bytes")


def test_append_returns_offset(tmp_path):
    with WAL(tmp_path / "database.wal") as wal:
        first = wal.append(b"A")
        second = wal.append(b"BC")

        assert first == 0
        assert second > first
