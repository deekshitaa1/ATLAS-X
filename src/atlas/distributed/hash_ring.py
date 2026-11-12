from __future__ import annotations

import bisect
import hashlib
import threading


class ConsistentHashRing:
    """Thread-safe consistent hash ring with virtual nodes."""

    def __init__(self, replicas: int = 100) -> None:
        if not isinstance(replicas, int) or isinstance(replicas, bool):
            raise TypeError("replicas must be an integer")
        if replicas <= 0:
            raise ValueError("replicas must be positive")

        self.replicas = replicas
        self._ring: dict[int, str] = {}
        self._sorted_hashes: list[int] = []
        self._nodes: set[str] = set()
        self._lock = threading.RLock()

    @staticmethod
    def _hash(value: str) -> int:
        digest = hashlib.sha256(value.encode("utf-8")).digest()
        return int.from_bytes(digest[:8], byteorder="big")

    def add_node(self, node: str) -> None:
        if not isinstance(node, str):
            raise TypeError("node must be a string")
        if not node:
            raise ValueError("node cannot be empty")

        with self._lock:
            if node in self._nodes:
                return

            for replica in range(self.replicas):
                position = self._hash(f"{node}:{replica}")
                self._ring[position] = node
                bisect.insort(self._sorted_hashes, position)

            self._nodes.add(node)

    def remove_node(self, node: str) -> None:
        with self._lock:
            if node not in self._nodes:
                return

            for replica in range(self.replicas):
                position = self._hash(f"{node}:{replica}")
                self._ring.pop(position, None)
                index = bisect.bisect_left(self._sorted_hashes, position)
                if index < len(self._sorted_hashes) and self._sorted_hashes[index] == position:
                    self._sorted_hashes.pop(index)

            self._nodes.remove(node)

    def get_node(self, key: str) -> str:
        if not isinstance(key, str):
            raise TypeError("key must be a string")
        if not key:
            raise ValueError("key cannot be empty")

        with self._lock:
            if not self._sorted_hashes:
                raise RuntimeError("No nodes available")

            position = self._hash(key)
            index = bisect.bisect_left(self._sorted_hashes, position)

            if index == len(self._sorted_hashes):
                index = 0

            return self._ring[self._sorted_hashes[index]]

    def get_nodes(self) -> list[str]:
        with self._lock:
            return sorted(self._nodes)

    def __len__(self) -> int:
        with self._lock:
            return len(self._nodes)

