import pytest

from atlas.lsm import LSMTree


def test_unflushed_put_survives_restart(tmp_path):
    db = LSMTree(tmp_path, memtable_limit=100)
    db.put("name", "Atlas")

    # Simulate process stop without graceful close.
    db._wal.close()

    recovered = LSMTree(tmp_path, memtable_limit=100)
    try:
        assert recovered.get("name") == "Atlas"
    finally:
        recovered.close()


def test_unflushed_delete_survives_restart(tmp_path):
    db = LSMTree(tmp_path, memtable_limit=100)
    db.put("name", "Atlas")
    db.flush()
    db.delete("name")

    db._wal.close()

    recovered = LSMTree(tmp_path, memtable_limit=100)
    try:
        assert recovered.get("name") is None
    finally:
        recovered.close()


def test_wal_recovery_preserves_latest_value(tmp_path):
    db = LSMTree(tmp_path, memtable_limit=100)
    db.put("version", 1)
    db.put("version", 2)

    db._wal.close()

    recovered = LSMTree(tmp_path, memtable_limit=100)
    try:
        assert recovered.get("version") == 2
    finally:
        recovered.close()

def test_none_value_survives_restart(tmp_path):
    db = LSMTree(tmp_path, memtable_limit=100)
    db.put("empty", None)
    db._wal.close()

    recovered = LSMTree(tmp_path, memtable_limit=100)
    try:
        assert recovered.contains("empty")
        assert recovered.get("empty") is None
    finally:
        recovered.close()
def simulate_crash(db):
    """Close only the WAL, without graceful LSM shutdown."""
    db._wal.close()


def test_crash_after_sstable_write_before_checkpoint(tmp_path, monkeypatch):
    db = LSMTree(tmp_path, memtable_limit=100)
    db.put("name", "Atlas")

    def crash_before_checkpoint():
        raise RuntimeError("Simulated crash before checkpoint")

    monkeypatch.setattr(db, "_checkpoint", crash_before_checkpoint)

    with pytest.raises(RuntimeError, match="Simulated crash"):
        db.flush()

    simulate_crash(db)

    recovered = LSMTree(tmp_path, memtable_limit=100)
    try:
        assert recovered.get("name") == "Atlas"
    finally:
        recovered.close()


def test_crash_during_compaction_before_checkpoint(tmp_path, monkeypatch):
    db = LSMTree(tmp_path, memtable_limit=2)
    db.put("a", 1)
    db.put("b", 2)
    db.flush()

    db.put("a", 10)
    db.flush()

    def crash_before_checkpoint():
        raise RuntimeError("Simulated compaction crash")

    monkeypatch.setattr(db, "_checkpoint", crash_before_checkpoint)

    with pytest.raises(RuntimeError, match="Simulated compaction crash"):
        db.compact()

    simulate_crash(db)

    recovered = LSMTree(tmp_path, memtable_limit=2)
    try:
        assert recovered.get("a") == 10
        assert recovered.get("b") == 2
    finally:
        recovered.close()


def test_recovery_after_multiple_flushes_and_crash(tmp_path):
    db = LSMTree(tmp_path, memtable_limit=2)

    db.put("a", 1)
    db.put("b", 2)
    db.flush()

    db.put("a", 3)
    db.put("c", 4)

    simulate_crash(db)

    recovered = LSMTree(tmp_path, memtable_limit=2)
    try:
        assert recovered.get("a") == 3
        assert recovered.get("b") == 2
        assert recovered.get("c") == 4
        assert len(recovered.scan()) == 3
    finally:
        recovered.close()

def test_wal_reset_clears_records_and_accepts_new_records(tmp_path):
    from atlas.wal import WAL

    wal = WAL(tmp_path / "reset.wal")
    try:
        wal.append(b"old-record")
        assert wal.read_all() == [b"old-record"]

        wal.reset()
        assert wal.read_all() == []

        wal.append(b"new-record")
        assert wal.read_all() == [b"new-record"]
    finally:
        wal.close()


def test_flush_rotates_wal_and_preserves_data(tmp_path):
    db = LSMTree(tmp_path, memtable_limit=100)
    db.put("city", "Mysuru")

    db.flush()

    try:
        assert db._wal.read_all() == []
        assert db.get("city") == "Mysuru"
    finally:
        db.close()


def test_data_survives_restart_after_wal_rotation(tmp_path):
    db = LSMTree(tmp_path, memtable_limit=100)
    db.put("city", "Mysuru")
    db.flush()
    db._wal.close()

    recovered = LSMTree(tmp_path, memtable_limit=100)
    try:
        assert recovered.get("city") == "Mysuru"
        assert recovered._wal.read_all() == []
    finally:
        recovered.close()


def test_compaction_rotates_wal(tmp_path):
    db = LSMTree(tmp_path, memtable_limit=2)
    db.put("a", 1)
    db.put("b", 2)
    db.flush()

    db.put("a", 3)
    db.flush()

    db.compact()

    try:
        assert db._wal.read_all() == []
        assert db.get("a") == 3
        assert db.get("b") == 2
    finally:
        db.close()

def test_batch_put_and_delete(tmp_path):
    db = LSMTree(tmp_path)
    try:
        db.put("old", 1)
        db.batch([
            ("put", "name", "Atlas"),
            ("put", "city", "Mysuru"),
            ("put", "version", 1),
            ("delete", "old"),
        ])

        assert db.get("name") == "Atlas"
        assert db.get("city") == "Mysuru"
        assert db.get("version") == 1
        assert not db.contains("old")
    finally:
        db.close()


def test_batch_survives_crash(tmp_path):
    db = LSMTree(tmp_path)
    db.batch([
        ("put", "name", "Atlas"),
        ("put", "city", "Mysuru"),
    ])
    db._wal.close()

    recovered = LSMTree(tmp_path)
    try:
        assert recovered.get("name") == "Atlas"
        assert recovered.get("city") == "Mysuru"
    finally:
        recovered.close()


def test_invalid_batch_does_not_change_data(tmp_path):
    db = LSMTree(tmp_path)
    try:
        db.put("existing", 10)

        with pytest.raises(ValueError):
            db.batch([
                ("put", "new", 20),
                ("invalid", "bad"),
            ])

        assert db.get("existing") == 10
        assert not db.contains("new")
    finally:
        db.close()
