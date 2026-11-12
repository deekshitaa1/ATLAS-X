
import pytest

from atlas.lsm import LSMTree


def test_put_and_get(tmp_path):
    with LSMTree(tmp_path) as db:
        db.put("name", "Atlas")
        assert db.get("name") == "Atlas"


def test_update_key(tmp_path):
    with LSMTree(tmp_path, memtable_limit=10) as db:
        db.put("version", 1)
        db.put("version", 2)
        assert db.get("version") == 2


def test_delete_key(tmp_path):
    with LSMTree(tmp_path) as db:
        db.put("name", "Atlas")
        db.delete("name")
        assert db.get("name") is None


def test_memtable_flush(tmp_path):
    with LSMTree(tmp_path, memtable_limit=2) as db:
        db.put("a", 1)
        db.put("b", 2)

        assert len(list(tmp_path.glob("*.sst"))) == 1
        assert db.get("a") == 1


def test_restart_recovery(tmp_path):
    with LSMTree(tmp_path, memtable_limit=2) as db:
        db.put("a", 1)
        db.put("b", 2)

    with LSMTree(tmp_path) as db:
        assert db.get("a") == 1
        assert db.get("b") == 2


def test_newer_sstable_wins(tmp_path):
    with LSMTree(tmp_path, memtable_limit=1) as db:
        db.put("a", 1)
        db.put("a", 2)
        assert db.get("a") == 2


def test_tombstone_survives_restart(tmp_path):
    with LSMTree(tmp_path, memtable_limit=1) as db:
        db.put("a", 1)
        db.delete("a")

    with LSMTree(tmp_path) as db:
        assert db.get("a") is None


def test_scan_prefix(tmp_path):
    with LSMTree(tmp_path, memtable_limit=2) as db:
        db.put("user:1", "Alice")
        db.put("user:2", "Bob")
        db.put("item:1", "Book")

        assert db.scan("user:") == {
            "user:1": "Alice",
            "user:2": "Bob",
        }


def test_compaction(tmp_path):
    with LSMTree(tmp_path, memtable_limit=1) as db:
        db.put("a", 1)
        db.put("b", 2)
        db.put("a", 3)

        db.compact()

        assert db.get("a") == 3
        assert db.get("b") == 2
        assert len(list(tmp_path.glob("*.sst"))) == 1


def test_compaction_removes_deleted_key(tmp_path):
    with LSMTree(tmp_path, memtable_limit=1) as db:
        db.put("a", 1)
        db.delete("a")

        db.compact()

        assert db.get("a") is None
        assert len(list(tmp_path.glob("*.sst"))) == 1


def test_invalid_key(tmp_path):
    with LSMTree(tmp_path) as db, pytest.raises(ValueError):
        db.put("", 1)


def test_closed_tree_rejects_operations(tmp_path):
    db = LSMTree(tmp_path)
    db.close()

    with pytest.raises(RuntimeError):
        db.get("a")
