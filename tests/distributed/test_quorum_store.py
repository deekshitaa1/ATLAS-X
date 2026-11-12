import pytest

from atlas.distributed.hash_ring import ConsistentHashRing
from atlas.distributed.quorum import QuorumConfig
from atlas.distributed.replication import ReplicationManager
from atlas.distributed.store import DistributedStore


def create_store():
    ring = ConsistentHashRing(replicas=100)
    for node in ("node-1", "node-2", "node-3"):
        ring.add_node(node)
    manager = ReplicationManager(ring, replication_factor=3)
    return DistributedStore(manager)


def test_quorum_write_and_read():
    store = create_store()
    config = QuorumConfig(3, 2, 2)

    written = store.quorum_put("key-1", "atlas", config)

    assert len(written) == 3
    assert store.quorum_get("key-1", config) == "atlas"


def test_quorum_write_fails_when_insufficient_nodes():
    store = create_store()
    config = QuorumConfig(3, 2, 2)

    for node in store.manager.get_replicas("key-2")[:2]:
        store.registry.mark_failed(node)

    with pytest.raises(RuntimeError, match="Write quorum"):
        store.quorum_put("key-2", "value", config)


def test_quorum_read_fails_when_insufficient_nodes():
    store = create_store()
    config = QuorumConfig(3, 2, 2)

    store.quorum_put("key-3", "value", config)

    for node in store.manager.get_replicas("key-3")[:2]:
        store.registry.mark_failed(node)

    with pytest.raises(RuntimeError, match="Read quorum"):
        store.quorum_get("key-3", config)


def test_quorum_write_with_one_failed_replica():
    store = create_store()
    config = QuorumConfig(3, 2, 2)

    failed = store.manager.get_replicas("key-4")[0]
    store.registry.mark_failed(failed)

    written = store.quorum_put("key-4", "value", config)

    assert len(written) == 2
    assert failed not in written


def test_quorum_read_with_one_failed_replica():
    store = create_store()
    config = QuorumConfig(3, 2, 2)

    store.quorum_put("key-5", "value", config)
    failed = store.manager.get_replicas("key-5")[0]
    store.registry.mark_failed(failed)

    assert store.quorum_get("key-5", config) == "value"


def test_quorum_rejects_insufficient_replica_configuration():
    store = create_store()
    config = QuorumConfig(4, 2, 3)

    with pytest.raises(RuntimeError, match="Insufficient configured replicas"):
        store.quorum_put("key-6", "value", config)
