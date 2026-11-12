from atlas.distributed.hash_ring import ConsistentHashRing
from atlas.distributed.replication import ReplicationManager
from atlas.distributed.store import DistributedStore
from atlas.distributed.versioning import VersionedValue


def create_store():
    ring = ConsistentHashRing(replicas=100)
    for node in ("node-1", "node-2", "node-3"):
        ring.add_node(node)
    return DistributedStore(
        ReplicationManager(ring, replication_factor=3)
    )


def test_reads_survive_two_node_failures():
    store = create_store()
    replicas = store.put("failure-key", "durable-value")

    store.registry.mark_failed(replicas[0])
    store.registry.mark_failed(replicas[1])

    assert store.get("failure-key") == "durable-value"


def test_multiple_node_recovery_restores_replicas():
    store = create_store()
    replicas = store.put("recovery-key", "ATLAS-X")

    for node in replicas[:2]:
        store.registry.mark_failed(node)

    for node in replicas[:2]:
        store.recover_node(node)

    for node in replicas:
        assert store.get_node_data(node)["recovery-key"] == "ATLAS-X"


def test_repeated_recovery_preserves_latest_version():
    store = create_store()
    replicas = store.manager.get_replicas("version-key")

    store._nodes[replicas[0]]["version-key"] = VersionedValue(1, "old")
    store._nodes[replicas[1]]["version-key"] = VersionedValue(7, "latest")
    store._nodes[replicas[2]]["version-key"] = VersionedValue(4, "middle")

    for _ in range(2):
        store.registry.mark_failed(replicas[0])
        store.recover_node(replicas[0])

    for node in replicas:
        assert store.get_node_data(node)["version-key"] == VersionedValue(
            7, "latest"
        )


def test_anti_entropy_does_not_repair_without_majority():
    store = create_store()
    replicas = store.manager.get_replicas("tie-key")

    store._nodes[replicas[0]]["tie-key"] = "A"
    store._nodes[replicas[1]]["tie-key"] = "B"
    store._nodes[replicas[2]]["tie-key"] = "C"

    assert store.repair_inconsistent_replicas("tie-key") == []

    for node, value in zip(replicas, ("A", "B", "C")):
        assert store.get_node_data(node)["tie-key"] == value
