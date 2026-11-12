import pytest

from atlas.distributed.hash_ring import ConsistentHashRing


def test_add_and_get_node():
    ring = ConsistentHashRing()
    ring.add_node("node-1")
    assert ring.get_node("customer-1") == "node-1"


def test_empty_ring_rejects_lookup():
    ring = ConsistentHashRing()
    with pytest.raises(RuntimeError, match="No nodes"):
        ring.get_node("key")


def test_duplicate_node_is_ignored():
    ring = ConsistentHashRing()
    ring.add_node("node-1")
    ring.add_node("node-1")
    assert len(ring) == 1


def test_remove_node():
    ring = ConsistentHashRing()
    ring.add_node("node-1")
    ring.remove_node("node-1")
    assert len(ring) == 0


def test_remaining_node_handles_all_keys():
    ring = ConsistentHashRing()
    ring.add_node("node-1")
    ring.add_node("node-2")
    ring.remove_node("node-1")

    for number in range(100):
        assert ring.get_node(f"key-{number}") == "node-2"


def test_deterministic_routing():
    first = ConsistentHashRing()
    second = ConsistentHashRing()

    for node in ("node-1", "node-2", "node-3"):
        first.add_node(node)
        second.add_node(node)

    for number in range(100):
        key = f"key-{number}"
        assert first.get_node(key) == second.get_node(key)


def test_invalid_node_rejected():
    ring = ConsistentHashRing()
    with pytest.raises(ValueError):
        ring.add_node("")


def test_invalid_replicas_rejected():
    with pytest.raises(ValueError):
        ConsistentHashRing(replicas=0)

def test_keys_are_reasonably_balanced():
    ring = ConsistentHashRing(replicas=100)
    nodes = ["node-1", "node-2", "node-3"]

    for node in nodes:
        ring.add_node(node)

    counts = {node: 0 for node in nodes}
    for number in range(5000):
        counts[ring.get_node(f"customer-{number}")] += 1

    for count in counts.values():
        assert 1200 <= count <= 2100


def test_adding_node_moves_only_a_subset_of_keys():
    ring = ConsistentHashRing(replicas=100)
    for node in ("node-1", "node-2", "node-3"):
        ring.add_node(node)

    keys = [f"customer-{number}" for number in range(5000)]
    before = {key: ring.get_node(key) for key in keys}

    ring.add_node("node-4")
    after = {key: ring.get_node(key) for key in keys}

    moved = sum(before[key] != after[key] for key in keys)
    assert 500 < moved < 2000
    assert all(after[key] == "node-4" for key in keys if before[key] != after[key])
