from concurrent.futures import ThreadPoolExecutor

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


def test_concurrent_writes_preserve_all_keys():
    store = create_store()

    def write(index):
        store.put(f"key-{index}", f"value-{index}")

    with ThreadPoolExecutor(max_workers=10) as executor:
        list(executor.map(write, range(100)))

    for index in range(100):
        assert store.get(f"key-{index}") == f"value-{index}"


def test_concurrent_versioned_writes_generate_unique_versions():
    store = create_store()

    def write(index):
        return store.versioned_put("shared-key", f"value-{index}")

    with ThreadPoolExecutor(max_workers=10) as executor:
        entries = list(executor.map(write, range(100)))

    versions = [entry.version for entry in entries]

    assert len(set(versions)) == 100
    assert max(versions) == 100


def test_concurrent_reads_and_writes_are_safe():
    store = create_store()
    store.put("shared-key", "initial")

    def write(index):
        store.put("shared-key", f"value-{index}")

    def read(_):
        return store.get("shared-key")

    with ThreadPoolExecutor(max_workers=10) as executor:
        writes = [executor.submit(write, i) for i in range(50)]
        reads = [executor.submit(read, i) for i in range(50)]

        for future in writes + reads:
            future.result()

    assert store.get("shared-key").startswith("value-")


def test_concurrent_versioned_writes_replicate_latest_entry():
    store = create_store()

    def write(index):
        return store.versioned_put("replicated-key", f"value-{index}")

    with ThreadPoolExecutor(max_workers=10) as executor:
        entries = list(executor.map(write, range(50)))

    latest = max(entries, key=lambda entry: entry.version)

    for node in store.manager.get_replicas("replicated-key"):
        assert (
            store.get_node_data(node)["replicated-key"] == latest
        )
