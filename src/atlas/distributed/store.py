from __future__ import annotations

import threading
from typing import Any

from atlas.distributed.replication import ReplicationManager


class DistributedStore:
    """Replicate key-value writes across selected storage nodes."""

    def __init__(self, manager: ReplicationManager) -> None:
        self.manager = manager
        self._nodes: dict[str, dict[str, Any]] = {
            node: {} for node in manager.ring.get_nodes()
        }
        self._lock = threading.RLock()

    def put(self, key: str, value: Any) -> list[str]:
        replicas = self.manager.get_replicas(key)

        with self._lock:
            for node in replicas:
                self._nodes.setdefault(node, {})[key] = value

        return replicas

    def get(self, key: str) -> Any:
        replicas = self.manager.get_replicas(key)

        with self._lock:
            for node in replicas:
                if key in self._nodes.get(node, {}):
                    return self._nodes[node][key]

        raise KeyError(key)

    def delete(self, key: str) -> list[str]:
        replicas = self.manager.get_replicas(key)

        with self._lock:
            for node in replicas:
                self._nodes.get(node, {}).pop(key, None)

        return replicas

    def get_node_data(self, node: str) -> dict[str, Any]:
        with self._lock:
            if node not in self._nodes:
                raise KeyError(node)
            return dict(self._nodes[node])
