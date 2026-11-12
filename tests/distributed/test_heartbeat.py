import time

import pytest

from atlas.distributed.heartbeat import HeartbeatMonitor


def test_heartbeat_marks_node_alive():
    monitor = HeartbeatMonitor(timeout_seconds=5)
    monitor.heartbeat("node-1")
    assert monitor.is_alive("node-1")


def test_unknown_node_is_not_alive():
    monitor = HeartbeatMonitor()
    assert not monitor.is_alive("unknown")


def test_stale_heartbeat_detects_failed_node():
    monitor = HeartbeatMonitor(timeout_seconds=0.01)
    monitor.heartbeat("node-1")
    time.sleep(0.03)
    assert "node-1" in monitor.failed_nodes()
    assert not monitor.is_alive("node-1")


def test_new_heartbeat_restores_node():
    monitor = HeartbeatMonitor(timeout_seconds=0.01)
    monitor.heartbeat("node-1")
    time.sleep(0.03)
    monitor.heartbeat("node-1")
    assert monitor.is_alive("node-1")


def test_invalid_timeout_rejected():
    with pytest.raises(ValueError):
        HeartbeatMonitor(timeout_seconds=0)
