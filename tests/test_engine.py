
import pytest

from atlas.engine import StorageEngine


def test_put_and_get(tmp_path):
    with StorageEngine(tmp_path) as db:
        db.put("name", "Atlas")
        assert db.get("name") == "Atlas"


def test_get_missing_key(tmp_path):
    with StorageEngine(tmp_path) as db:
        assert db.get("missing") is None


def test_update_existing_key(tmp_path):
    with StorageEngine(tmp_path) as db:
        db.put("version", 1)
        db.put("version", 2)

        assert db.get("version") == 2


def test_delete_key(tmp_path):
    with StorageEngine(tmp_path) as db:
        db.put("name", "Atlas")

        assert db.delete("name") is True
        assert db.get("name") is None
        assert db.delete("name") is False


def test_scan_by_prefix(tmp_path):
    with StorageEngine(tmp_path) as db:
        db.put("user:1", "Alice")
        db.put("user:2", "Bob")
        db.put("product:1", "Laptop")

        assert db.scan("user:") == {
            "user:1": "Alice",
            "user:2": "Bob",
        }


def test_count(tmp_path):
    with StorageEngine(tmp_path) as db:
        db.put("a", 1)
        db.put("b", 2)

        assert db.count() == 2


def test_data_survives_restart(tmp_path):
    with StorageEngine(tmp_path) as db:
        db.put("name", "Atlas-X")
        db.put("version", 1)

    with StorageEngine(tmp_path) as db:
        assert db.get("name") == "Atlas-X"
        assert db.get("version") == 1


def test_delete_survives_restart(tmp_path):
    with StorageEngine(tmp_path) as db:
        db.put("temporary", "data")
        db.delete("temporary")

    with StorageEngine(tmp_path) as db:
        assert db.get("temporary") is None
        assert db.exists("temporary") is False


def test_exists(tmp_path):
    with StorageEngine(tmp_path) as db:
        db.put("active", True)

        assert db.exists("active") is True
        assert db.exists("missing") is False


def test_empty_key_rejected(tmp_path):
    with StorageEngine(tmp_path) as db, pytest.raises(ValueError):
        db.put("", "invalid")


def test_non_string_key_rejected(tmp_path):
    with StorageEngine(tmp_path) as db, pytest.raises(TypeError):
        db.get(123)


def test_invalid_json_value_rejected(tmp_path):
    with StorageEngine(tmp_path) as db, pytest.raises(ValueError):
        db.put("invalid", float("nan"))


def test_closed_engine_rejects_operations(tmp_path):
    db = StorageEngine(tmp_path)
    db.close()

    with pytest.raises(RuntimeError):
        db.get("name")
