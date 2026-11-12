import pytest

from atlas.distributed.hash_ring import ConsistentHashRing
from atlas.distributed.replication import ReplicationManager
from atlas.distributed.store import DistributedStore


def create_store():
    ring = ConsistentHashRing(replicas=100)
    for node in ("node-1", "node-2", "node-3"):
        ring.add_node(node)
    manager = ReplicationManager(ring, replication_factor=3)
    return DistributedStore(manager)


def test_put_replicates_data_to_all_nodes():
    store = create_store()
    replicas = store.put("user:1", {"name": "Atlas"})
    assert len(replicas) == 3
    for node in replicas:
        assert store.get_node_data(node)["user:1"] == {"name": "Atlas"}


def test_get_returns_replicated_value():
    store = create_store()
    store.put("user:2", "Deeksha")
    assert store.get("user:2") == "Deeksha"


def test_delete_removes_data_from_all_replicas():
    store = create_store()
    replicas = store.put("user:3", "value")
    store.delete("user:3")
    for node in replicas:
        assert "user:3" not in store.get_node_data(node)


def test_get_missing_key_raises_key_error():
    store = create_store()
    with pytest.raises(KeyError):
        store.get("missing")


def test_unknown_node_raises_key_error():
    store = create_store()
    with pytest.raises(KeyError):
        store.get_node_data("unknown-node")


def test_replication_preserves_independent_keys():
    store = create_store()
    store.put("key-1", "value-1")
    store.put("key-2", "value-2")
    assert store.get("key-1") == "value-1"
    assert store.get("key-2") == "value-2"
