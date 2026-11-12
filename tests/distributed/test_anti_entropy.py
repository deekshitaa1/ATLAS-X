from atlas.distributed.hash_ring import ConsistentHashRing
from atlas.distributed.replication import ReplicationManager
from atlas.distributed.store import DistributedStore


def create_store():
    ring = ConsistentHashRing(replicas=100)
    for node in ("node-1", "node-2", "node-3"):
        ring.add_node(node)
    manager = ReplicationManager(ring, replication_factor=3)
    return DistributedStore(manager)


def test_anti_entropy_repairs_inconsistent_replica():
    store = create_store()
    replicas = store.put("key-1", "correct-value")
    bad_node = replicas[0]

    store._nodes[bad_node]["key-1"] = "wrong-value"

    repaired = store.repair_inconsistent_replicas("key-1")

    assert repaired == [bad_node]
    assert store.get_node_data(bad_node)["key-1"] == "correct-value"


def test_anti_entropy_does_nothing_when_consistent():
    store = create_store()
    store.put("key-2", "same-value")

    assert store.repair_inconsistent_replicas("key-2") == []


def test_anti_entropy_ignores_missing_replicas():
    store = create_store()
    store.put("key-3", "value")
    replicas = store.manager.get_replicas("key-3")

    store._nodes[replicas[0]].pop("key-3")

    assert store.repair_inconsistent_replicas("key-3") == []
