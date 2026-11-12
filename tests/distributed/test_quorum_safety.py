import pytest

from atlas.distributed.hash_ring import ConsistentHashRing
from atlas.distributed.quorum import QuorumConfig
from atlas.distributed.replication import ReplicationManager
from atlas.distributed.store import DistributedStore
from atlas.distributed.versioning import VersionedValue


def create_store():
    ring = ConsistentHashRing(replicas=100)
    for node in ("node-1", "node-2", "node-3"):
        ring.add_node(node)
    manager = ReplicationManager(ring, replication_factor=3)
    return DistributedStore(manager)


def test_failed_quorum_write_does_not_change_data():
    store = create_store()
    store.put("key", "old")
    replicas = store.manager.get_replicas("key")

    store.registry.mark_failed(replicas[1])
    store.registry.mark_failed(replicas[2])

    with pytest.raises(RuntimeError, match="Write quorum"):
        store.quorum_put("key", "new", QuorumConfig(3, 2, 2))

    assert store.get_node_data(replicas[0])["key"] == "old"


def test_successful_quorum_write_updates_available_replicas():
    store = create_store()
    store.quorum_put("key", "value", QuorumConfig(3, 2, 2))

    for node in store.manager.get_replicas("key"):
        assert store.get_node_data(node)["key"] == "value"


def test_quorum_get_selects_highest_version():
    store = create_store()
    replicas = store.manager.get_replicas("key")

    store._nodes[replicas[0]]["key"] = VersionedValue(1, "old")
    store._nodes[replicas[1]]["key"] = VersionedValue(3, "new")
    store._nodes[replicas[2]]["key"] = VersionedValue(2, "middle")

    result = store.quorum_get("key", QuorumConfig(3, 2, 2))
    assert result == VersionedValue(3, "new")


def test_quorum_get_rejects_mixed_value_types():
    store = create_store()
    replicas = store.manager.get_replicas("key")

    store._nodes[replicas[0]]["key"] = VersionedValue(1, "versioned")
    store._nodes[replicas[1]]["key"] = "plain"
    store._nodes[replicas[2]]["key"] = VersionedValue(2, "newer")

    with pytest.raises(RuntimeError, match="Mixed"):
        store.quorum_get("key", QuorumConfig(3, 2, 2))


def test_consistency_repair_does_not_choose_tied_majority():
    store = create_store()
    replicas = store.manager.get_replicas("key")

    store._nodes[replicas[0]]["key"] = "A"
    store._nodes[replicas[1]]["key"] = "B"
    store._nodes[replicas[2]]["key"] = "C"

    repaired = store.repair_inconsistent_replicas("key")

    assert repaired == []
    assert [store.get_node_data(node)["key"] for node in replicas] == [
        "A", "B", "C"
    ]
