from atlas.distributed.hash_ring import ConsistentHashRing
from atlas.distributed.replication import ReplicationManager
from atlas.distributed.store import DistributedStore


def create_store():
    ring = ConsistentHashRing(replicas=100)
    for node in ("node-1", "node-2", "node-3"):
        ring.add_node(node)
    return DistributedStore(
        ReplicationManager(ring, replication_factor=3)
    )


def test_versioned_put_assigns_version():
    store = create_store()
    entry = store.versioned_put("key-1", "ATLAS")
    assert entry.version == 1
    assert entry.value == "ATLAS"


def test_versions_increase_on_updates():
    store = create_store()
    first = store.versioned_put("key-1", "old")
    second = store.versioned_put("key-1", "new")
    assert second.version > first.version


def test_versioned_get_returns_latest_value():
    store = create_store()
    store.versioned_put("key-1", "old")
    latest = store.versioned_put("key-1", "new")
    assert store.versioned_get("key-1") == latest


def test_versioned_write_replicates_to_available_nodes():
    store = create_store()
    replicas = store.versioned_put("key-2", "value")
    for node in store.manager.get_replicas("key-2"):
        assert store.get_node_data(node)["key-2"] == replicas


def test_versioned_get_missing_key_raises():
    import pytest

    store = create_store()
    with pytest.raises(KeyError):
        store.versioned_get("missing")
