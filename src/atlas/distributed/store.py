from __future__ import annotations

import threading
from typing import Any

from atlas.distributed.node_registry import NodeRegistry
from atlas.distributed.replication import ReplicationManager
from atlas.distributed.versioning import VersionClock, VersionedValue


class DistributedStore:
    """Replicate key-value writes across available storage nodes."""

    def __init__(self, manager: ReplicationManager) -> None:
        self.manager = manager
        self._nodes: dict[str, dict[str, Any]] = {
            node: {} for node in manager.ring.get_nodes()
        }
        self.registry = NodeRegistry(list(self._nodes))
        self._version_clock = VersionClock()
        self._lock = threading.RLock()

    def put(self, key: str, value: Any) -> list[str]:
        replicas = self.manager.get_replicas(key)
        available = [
            node for node in replicas if self.registry.is_available(node)
        ]

        if not available:
            raise RuntimeError("No available replicas")

        with self._lock:
            for node in available:
                self._nodes[node][key] = value

        return available

    def get(self, key: str) -> Any:
        replicas = self.manager.get_replicas(key)

        with self._lock:
            for node in replicas:
                if self.registry.is_available(node) and key in self._nodes[node]:
                    return self._nodes[node][key]

        raise KeyError(key)

    def delete(self, key: str) -> list[str]:
        replicas = self.manager.get_replicas(key)
        available = [
            node for node in replicas if self.registry.is_available(node)
        ]

        with self._lock:
            for node in available:
                self._nodes[node].pop(key, None)

        return available

    def recover_node(self, node: str) -> int:
        with self._lock:
            if node not in self._nodes:
                raise KeyError(node)

            self.registry.mark_recovered(node)
            repaired = 0

            for key, value in list(self._nodes[node].items()):
                replicas = self.manager.get_replicas(key)
                available = [
                    replica for replica in replicas
                    if self.registry.is_available(replica)
                ]
                if available:
                    for replica in available:
                        self._nodes[replica][key] = value

            for key in self._all_known_keys():
                replicas = self.manager.get_replicas(key)
                if node in replicas and key not in self._nodes[node]:
                    for replica in replicas:
                        if replica != node and key in self._nodes[replica]:
                            self._nodes[node][key] = self._nodes[replica][key]
                            repaired += 1
                            break

            return repaired

    def _all_known_keys(self) -> set[str]:
        return {
            key
            for data in self._nodes.values()
            for key in data
        }


    def repair_inconsistent_replicas(self, key: str) -> list[str]:
        from atlas.distributed.consistency import ConsistencyChecker

        replicas = self.manager.get_replicas(key)

        with self._lock:
            values = {
                node: self._nodes[node][key]
                for node in replicas
                if self.registry.is_available(node)
                and key in self._nodes[node]
            }

            if len(values) < 2:
                return []

            checker = ConsistencyChecker()
            outliers = checker.find_outliers(values)

            if not outliers:
                return []

            counts = {}
            for value in values.values():
                digest = checker._digest(value)
                counts[digest] = counts.get(digest, 0) + 1

            majority_digest = max(counts, key=counts.get)
            majority_value = next(
                value for value in values.values()
                if checker._digest(value) == majority_digest
            )

            for node in outliers:
                self._nodes[node][key] = majority_value

            return outliers


    def quorum_put(self, key: str, value: Any, config) -> list[str]:
        replicas = self.manager.get_replicas(key)
        if len(replicas) < config.replicas:
            raise RuntimeError("Insufficient configured replicas")

        available = [
            node for node in replicas
            if self.registry.is_available(node)
        ]

        with self._lock:
            written = []
            for node in available:
                self._nodes[node][key] = value
                written.append(node)

            if len(written) < config.write_quorum:
                raise RuntimeError("Write quorum not reached")

            return written

    def quorum_get(self, key: str, config) -> Any:
        replicas = self.manager.get_replicas(key)
        if len(replicas) < config.replicas:
            raise RuntimeError("Insufficient configured replicas")

        with self._lock:
            values = [
                self._nodes[node][key]
                for node in replicas
                if self.registry.is_available(node)
                and key in self._nodes[node]
            ]

            if len(values) < config.read_quorum:
                raise RuntimeError("Read quorum not reached")

            return values[0]


    def versioned_put(self, key: str, value: Any) -> VersionedValue:
        replicas = self.manager.get_replicas(key)
        available = [
            node for node in replicas
            if self.registry.is_available(node)
        ]

        if not available:
            raise RuntimeError("No available replicas")

        with self._lock:
            current_versions = [
                self._nodes[node][key].version
                for node in replicas
                if key in self._nodes[node]
                and isinstance(self._nodes[node][key], VersionedValue)
            ]
            current = max(current_versions, default=0)
            self._version_clock._version = max(
                self._version_clock.current, current
            )
            entry = VersionedValue(self._version_clock.next_version(), value)

            for node in available:
                self._nodes[node][key] = entry

            return entry

    def versioned_get(self, key: str) -> VersionedValue:
        replicas = self.manager.get_replicas(key)

        with self._lock:
            entries = [
                self._nodes[node][key]
                for node in replicas
                if self.registry.is_available(node)
                and isinstance(self._nodes[node].get(key), VersionedValue)
            ]

            if not entries:
                raise KeyError(key)

            return max(entries, key=lambda entry: entry.version)

    def get_node_data(self, node: str) -> dict[str, Any]:
        with self._lock:
            if node not in self._nodes:
                raise KeyError(node)
            return dict(self._nodes[node])
