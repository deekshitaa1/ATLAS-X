import pytest

from atlas.distributed.hash_ring import ConsistentHashRing
from atlas.distributed.replication import ReplicationManager
from atlas.distributed.store import DistributedStore


def create_store():
    ring = ConsistentHashRing(replicas=100)
    for node in ("node-1", "node-2", "node-3"):
        ring.add_node(node)
    return DistributedStore(ReplicationManager(ring, replication_factor=3))


def test_failed_node_is_unavailable():
    store = create_store()
    store.registry.mark_failed("node-1")
    assert not store.registry.is_available("node-1")


def test_read_works_when_one_replica_fails():
    store = create_store()
    replicas = store.put("key-1", "value-1")
    store.registry.mark_failed(replicas[0])
    assert store.get("key-1") == "value-1"


def test_write_skips_failed_replica():
    store = create_store()
    replicas = store.manager.get_replicas("key-2")
    store.registry.mark_failed(replicas[0])
    written = store.put("key-2", "value-2")
    assert replicas[0] not in written
    assert store.get("key-2") == "value-2"


def test_all_failed_replicas_reject_write():
    store = create_store()
    replicas = store.manager.get_replicas("key-3")
    for node in replicas:
        store.registry.mark_failed(node)

    with pytest.raises(RuntimeError, match="No available replicas"):
        store.put("key-3", "value-3")


def test_recovered_node_becomes_available():
    store = create_store()
    store.registry.mark_failed("node-1")
    store.registry.mark_recovered("node-1")
    assert store.registry.is_available("node-1")

def test_recovery_restores_missing_replica_data():
    store = create_store()
    replicas = store.manager.get_replicas("recovery-key")
    store.put("recovery-key", "important-data")

    failed_node = replicas[0]
    store.registry.mark_failed(failed_node)
    store._nodes[failed_node].clear()

    repaired = store.recover_node(failed_node)

    assert repaired == 1
    assert store.get_node_data(failed_node)["recovery-key"] == "important-data"


def test_recovery_does_not_lose_existing_data():
    store = create_store()
    store.put("key-a", "value-a")
    store.put("key-b", "value-b")

    store.registry.mark_failed("node-1")
    store.recover_node("node-1")

    assert store.get("key-a") == "value-a"
    assert store.get("key-b") == "value-b"


def test_recovery_rejects_unknown_node():
    store = create_store()

    with pytest.raises(KeyError):
        store.recover_node("unknown-node")
