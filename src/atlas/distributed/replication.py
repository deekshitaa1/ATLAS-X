from atlas.distributed.hash_ring import ConsistentHashRing


class ReplicationManager:
    """Assign primary and replica nodes using a consistent hash ring."""

    def __init__(self, ring: ConsistentHashRing, replication_factor: int = 3):
        if not isinstance(replication_factor, int) or isinstance(replication_factor, bool):
            raise TypeError("replication_factor must be an integer")
        if replication_factor <= 0:
            raise ValueError("replication_factor must be positive")

        self.ring = ring
        self.replication_factor = replication_factor

    def get_replicas(self, key: str) -> list[str]:
        if not isinstance(key, str):
            raise TypeError("key must be a string")
        if not key:
            raise ValueError("key cannot be empty")

        nodes = self.ring.get_nodes()
        if not nodes:
            raise RuntimeError("No nodes available")

        count = min(self.replication_factor, len(nodes))
        primary = self.ring.get_node(key)
        ordered = [primary]

        # Walk clockwise from the key's hash position.
        import bisect

        position = self.ring._hash(key)
        hashes = self.ring._sorted_hashes

        for index in range(bisect.bisect_left(hashes, position), len(hashes)):
            node = self.ring._ring[hashes[index]]
            if node not in ordered:
                ordered.append(node)
            if len(ordered) == count:
                return ordered

        for index in range(bisect.bisect_left(hashes, position)):
            node = self.ring._ring[hashes[index]]
            if node not in ordered:
                ordered.append(node)
            if len(ordered) == count:
                return ordered

        return ordered
