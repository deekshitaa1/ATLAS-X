import pytest

from atlas.distributed.hash_ring import ConsistentHashRing
from atlas.distributed.replication import ReplicationManager


def create_ring():
    ring = ConsistentHashRing(replicas=100)
    for node in ("node-1", "node-2", "node-3"):
        ring.add_node(node)
    return ring


def test_replication_returns_three_distinct_nodes():
    manager = ReplicationManager(create_ring(), replication_factor=3)
    replicas = manager.get_replicas("customer-1")
    assert len(replicas) == 3
    assert len(set(replicas)) == 3


def test_primary_node_is_first():
    ring = create_ring()
    manager = ReplicationManager(ring, replication_factor=3)
    assert manager.get_replicas("customer-1")[0] == ring.get_node("customer-1")


def test_replication_factor_larger_than_node_count():
    ring = ConsistentHashRing()
    ring.add_node("node-1")
    ring.add_node("node-2")
    manager = ReplicationManager(ring, replication_factor=3)
    assert len(manager.get_replicas("key-1")) == 2


def test_empty_ring_rejects_replication():
    ring = ConsistentHashRing()
    manager = ReplicationManager(ring)
    with pytest.raises(RuntimeError, match="No nodes"):
        manager.get_replicas("key-1")


def test_invalid_replication_factor():
    with pytest.raises(ValueError):
        ReplicationManager(create_ring(), replication_factor=0)
