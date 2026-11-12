import pytest

from atlas.persistent_mvcc import PersistentMVCCStore


def test_persistent_put_survives_restart(tmp_path):
    store = PersistentMVCCStore(tmp_path)
    store.put("name", "Atlas")
    store.close()

    store = PersistentMVCCStore(tmp_path)
    assert store.get("name") == "Atlas"
    store.close()


def test_persistent_delete_survives_restart(tmp_path):
    store = PersistentMVCCStore(tmp_path)
    store.put("key", "value")
    store.delete("key")
    store.close()

    store = PersistentMVCCStore(tmp_path)
    assert store.get("key") is None
    assert not store.contains("key")
    store.close()


def test_persistent_transaction_survives_restart(tmp_path):
    store = PersistentMVCCStore(tmp_path)
    with store.begin() as tx:
        tx.put("account_a", 500)
        tx.put("account_b", 1000)
    store.close()

    store = PersistentMVCCStore(tmp_path)
    assert store.scan() == {"account_a": 500, "account_b": 1000}
    store.close()


def test_persistent_rollback_is_not_saved(tmp_path):
    store = PersistentMVCCStore(tmp_path)
    with pytest.raises(RuntimeError), store.begin() as tx:
        tx.put("key", "not-saved")
        raise RuntimeError("rollback")
    store.close()

    store = PersistentMVCCStore(tmp_path)
    assert not store.contains("key")
    store.close()


def test_persistent_snapshot_survives_restart(tmp_path):
    store = PersistentMVCCStore(tmp_path)
    store.put("key", "old")
    old_snapshot = store.snapshot()
    store.put("key", "new")
    store.close()

    store = PersistentMVCCStore(tmp_path)
    assert store.get("key", old_snapshot) == "old"
    assert store.get("key") == "new"
    store.close()


def test_persistent_write_conflict(tmp_path):
    store = PersistentMVCCStore(tmp_path)
    store.put("key", "initial")
    first = store.begin()
    second = store.begin()

    first.put("key", "first")
    second.put("key", "second")
    first.commit()

    with pytest.raises(RuntimeError, match="Write conflict"):
        second.commit()

    assert store.get("key") == "first"
    store.close()


def test_persistent_store_rejects_writes_after_close(tmp_path):
    store = PersistentMVCCStore(tmp_path)
    store.close()

    with pytest.raises(RuntimeError, match="closed"):
        store.put("key", "value")

def test_transaction_commit_recovers_after_simulated_crash(tmp_path):
    store = PersistentMVCCStore(tmp_path)
    tx = store.begin()
    tx.put("a", 10)
    tx.put("b", 20)
    tx.commit()

    # Simulate process termination without normal store.close().
    store._wal.close()

    recovered = PersistentMVCCStore(tmp_path)
    assert recovered.scan() == {"a": 10, "b": 20}
    recovered.close()


def test_incomplete_wal_tail_is_repaired(tmp_path):
    store = PersistentMVCCStore(tmp_path)
    store.put("key", "durable")
    store.close()

    with (tmp_path / "mvcc.wal").open("ab") as file:
        file.write(b"ATX1\x00")

    recovered = PersistentMVCCStore(tmp_path)
    assert recovered.get("key") == "durable"
    recovered.close()


def test_corrupted_wal_record_is_rejected(tmp_path):
    from atlas.persistent_mvcc import MVCCCorruptionError

    store = PersistentMVCCStore(tmp_path)
    store.put("key", "value")
    store.close()

    wal_path = tmp_path / "mvcc.wal"
    content = bytearray(wal_path.read_bytes())
    content[-1] ^= 0x01
    wal_path.write_bytes(content)

    with pytest.raises(MVCCCorruptionError):
        PersistentMVCCStore(tmp_path)


def test_failed_serialization_does_not_write_record(tmp_path):
    store = PersistentMVCCStore(tmp_path)

    with pytest.raises(ValueError):
        store.put("bad", float("nan"))

    assert not store.contains("bad")
    store.close()

    recovered = PersistentMVCCStore(tmp_path)
    assert not recovered.contains("bad")
    recovered.close()
