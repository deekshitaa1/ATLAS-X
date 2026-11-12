from __future__ import annotations

import threading
import time


class HeartbeatMonitor:
    """Track node heartbeat timestamps and detect stale nodes."""

    def __init__(self, timeout_seconds: float = 10.0) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

        self.timeout_seconds = timeout_seconds
        self._heartbeats: dict[str, float] = {}
        self._lock = threading.RLock()

    def heartbeat(self, node: str) -> None:
        if not isinstance(node, str) or not node:
            raise ValueError("node must be a non-empty string")

        with self._lock:
            self._heartbeats[node] = time.monotonic()

    def is_alive(self, node: str) -> bool:
        with self._lock:
            last_seen = self._heartbeats.get(node)
            if last_seen is None:
                return False
            return time.monotonic() - last_seen <= self.timeout_seconds

    def failed_nodes(self) -> list[str]:
        with self._lock:
            now = time.monotonic()
            return sorted(
                node
                for node, last_seen in self._heartbeats.items()
                if now - last_seen > self.timeout_seconds
            )

    def remove_node(self, node: str) -> None:
        with self._lock:
            self._heartbeats.pop(node, None)
