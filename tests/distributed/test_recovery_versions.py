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


def test_recovery_preserves_highest_version():
    store = create_store()
    replicas = store.manager.get_replicas("version-key")

    store._nodes[replicas[0]]["version-key"] = VersionedValue(1, "old")
    store._nodes[replicas[1]]["version-key"] = VersionedValue(3, "latest")
    store._nodes[replicas[2]]["version-key"] = VersionedValue(2, "middle")

    store.registry.mark_failed(replicas[0])
    store.recover_node(replicas[0])

    assert store.versioned_get("version-key") == VersionedValue(3, "latest")


def test_recovery_restores_latest_version_to_missing_replica():
    store = create_store()
    replicas = store.manager.get_replicas("restore-key")

    store._nodes[replicas[0]]["restore-key"] = VersionedValue(1, "old")
    store._nodes[replicas[1]]["restore-key"] = VersionedValue(5, "latest")
    store._nodes[replicas[2]]["restore-key"] = VersionedValue(3, "middle")

    store.registry.mark_failed(replicas[0])
    store._nodes[replicas[0]].clear()
    store.recover_node(replicas[0])

    assert store.get_node_data(replicas[0])["restore-key"] == VersionedValue(
        5, "latest"
    )


def test_recovery_does_not_overwrite_newer_replica():
    store = create_store()
    replicas = store.manager.get_replicas("safe-key")

    store._nodes[replicas[0]]["safe-key"] = VersionedValue(1, "old")
    store._nodes[replicas[1]]["safe-key"] = VersionedValue(4, "latest")
    store._nodes[replicas[2]]["safe-key"] = VersionedValue(2, "middle")

    store.registry.mark_failed(replicas[0])
    store.recover_node(replicas[0])

    assert store.get_node_data(replicas[1])["safe-key"] == VersionedValue(
        4, "latest"
    )
