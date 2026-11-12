import pytest

from atlas.mvcc import MVCCStore, Version


def test_versions_preserve_history():
    store = MVCCStore()
    first = store.put("key", "old")
    second = store.put("key", "new")
    assert store.get("key", first) == "old"
    assert store.get("key", second) == "new"


def test_snapshot_is_stable_after_new_write():
    store = MVCCStore()
    store.put("key", 10)
    snapshot = store.snapshot()
    store.put("key", 20)
    assert store.get("key", snapshot) == 10
    assert store.get("key") == 20


def test_delete_preserves_old_snapshot():
    store = MVCCStore()
    old = store.put("key", "value")
    store.delete("key")
    assert store.get("key", old) == "value"
    assert store.get("key") is None


def test_scan_uses_snapshot():
    store = MVCCStore()
    store.put("a", 1)
    snapshot = store.snapshot()
    store.put("b", 2)
    assert store.scan(snapshot) == {"a": 1}
    assert store.scan() == {"a": 1, "b": 2}


def test_invalid_snapshot_is_rejected():
    store = MVCCStore()
    with pytest.raises(ValueError):
        store.get("key", 1)


def test_invalid_key_is_rejected():
    store = MVCCStore()
    with pytest.raises(ValueError):
        store.put("", 1)


def test_version_is_immutable():
    version = Version(1, "value")
    with pytest.raises(AttributeError):
        version.sequence = 2

def test_transaction_reads_own_writes():
    store = MVCCStore()
    with store.begin() as tx:
        tx.put("key", "staged")
        assert tx.get("key") == "staged"


def test_transaction_commit_and_rollback():
    store = MVCCStore()
    tx = store.begin()
    tx.put("key", "committed")
    tx.commit()
    assert store.get("key") == "committed"

    tx = store.begin()
    tx.put("key", "discarded")
    tx.rollback()
    assert store.get("key") == "committed"


def test_snapshot_transaction_does_not_see_later_write():
    store = MVCCStore()
    store.put("key", "old")
    tx = store.begin()
    store.put("key", "new")
    assert tx.get("key") == "old"
    tx.rollback()


def test_concurrent_write_conflict_is_rejected():
    store = MVCCStore()
    store.put("key", "initial")
    first = store.begin()
    second = store.begin()

    first.put("key", "first")
    second.put("key", "second")
    first.commit()

    with pytest.raises(RuntimeError, match="Write conflict"):
        second.commit()

    assert store.get("key") == "first"


def test_transaction_context_rolls_back_on_error():
    store = MVCCStore()
    with pytest.raises(RuntimeError), store.begin() as tx:
        tx.put("key", "value")
        raise RuntimeError("simulated failure")
    assert not store.contains("key")


def test_mvcc_contains_stored_none():
    store = MVCCStore()
    store.put("key", None)
    assert store.contains("key")
    assert store.get("key") is None
