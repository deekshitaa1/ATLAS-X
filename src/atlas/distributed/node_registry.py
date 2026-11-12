from __future__ import annotations

import threading


class NodeRegistry:
    """Track available and unavailable storage nodes."""

    def __init__(self, nodes: list[str]) -> None:
        if len(set(nodes)) != len(nodes):
            raise ValueError("Node names must be unique")
        if any(not isinstance(node, str) or not node for node in nodes):
            raise ValueError("Node names must be non-empty strings")

        self._nodes = set(nodes)
        self._failed: set[str] = set()
        self._lock = threading.RLock()

    def mark_failed(self, node: str) -> None:
        with self._lock:
            if node not in self._nodes:
                raise KeyError(node)
            self._failed.add(node)

    def mark_recovered(self, node: str) -> None:
        with self._lock:
            if node not in self._nodes:
                raise KeyError(node)
            self._failed.discard(node)

    def is_available(self, node: str) -> bool:
        with self._lock:
            return node in self._nodes and node not in self._failed

    def available_nodes(self) -> list[str]:
        with self._lock:
            return sorted(self._nodes - self._failed)

    def failed_nodes(self) -> list[str]:
        with self._lock:
            return sorted(self._failed)
