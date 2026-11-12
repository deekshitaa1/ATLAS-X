from __future__ import annotations

from atlas.distributed.heartbeat import HeartbeatMonitor
from atlas.distributed.node_registry import NodeRegistry


class FailureDetector:
    """Synchronize heartbeat health with node availability."""

    def __init__(
        self,
        registry: NodeRegistry,
        monitor: HeartbeatMonitor,
    ) -> None:
        self.registry = registry
        self.monitor = monitor

    def heartbeat(self, node: str) -> None:
        self.monitor.heartbeat(node)
        self.registry.mark_recovered(node)

    def check_nodes(self) -> list[str]:
        failed = self.monitor.failed_nodes()

        for node in failed:
            if self.registry.is_available(node):
                self.registry.mark_failed(node)

        return failed

    def is_available(self, node: str) -> bool:
        self.check_nodes()
        return self.registry.is_available(node)
