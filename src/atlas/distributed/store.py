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

            repaired = 0
            keys = self._all_known_keys()

            for key in keys:
                replicas = self.manager.get_replicas(key)
                if node not in replicas:
                    continue

                available_sources = [
                    replica for replica in replicas
                    if replica != node
                    and self.registry.is_available(replica)
                    and key in self._nodes[replica]
                ]

                if not available_sources:
                    continue

                values = [
                    self._nodes[replica][key]
                    for replica in available_sources
                ]

                versioned = [
                    value for value in values
                    if isinstance(value, VersionedValue)
                ]

                if versioned:
                    if len(versioned) != len(values):
                        continue
                    selected = max(versioned, key=lambda entry: entry.version)
                    self._version_clock.observe(selected.version)
                else:
                    selected = values[0]

                if self._nodes[node].get(key) != selected:
                    self._nodes[node][key] = selected
                    repaired += 1

                for replica in available_sources:
                    current = self._nodes[replica][key]

                    if isinstance(selected, VersionedValue):
                        if (
                            not isinstance(current, VersionedValue)
                            or current.version < selected.version
                        ):
                            self._nodes[replica][key] = selected
                    elif current == selected:
                        continue

            self.registry.mark_recovered(node)
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
            digests = {
                node: checker._digest(value)
                for node, value in values.items()
            }

            counts: dict[str, int] = {}
            for digest in digests.values():
                counts[digest] = counts.get(digest, 0) + 1

            highest_count = max(counts.values())
            winners = [
                digest for digest, count in counts.items()
                if count == highest_count
            ]

            if len(winners) != 1 or highest_count <= len(values) // 2:
                return []

            majority_digest = winners[0]
            majority_value = next(
                values[node]
                for node in values
                if digests[node] == majority_digest
            )

            outliers = [
                node for node, digest in digests.items()
                if digest != majority_digest
            ]

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
            if len(available) < config.write_quorum:
                raise RuntimeError("Write quorum not reached")

            previous = {
                node: (key in self._nodes[node], self._nodes[node].get(key))
                for node in available
            }

            try:
                for node in available:
                    self._nodes[node][key] = value
            except Exception:
                for node, (existed, old_value) in previous.items():
                    if existed:
                        self._nodes[node][key] = old_value
                    else:
                        self._nodes[node].pop(key, None)
                raise

            return available

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

            versioned = [
                value for value in values
                if isinstance(value, VersionedValue)
            ]

            if versioned:
                if len(versioned) != len(values):
                    raise RuntimeError("Mixed versioned and unversioned replicas")
                return max(versioned, key=lambda entry: entry.version)

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
            self._version_clock.observe(max(current_versions, default=0))
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
