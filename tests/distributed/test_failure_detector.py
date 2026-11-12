import time

from atlas.distributed.failure_detector import FailureDetector
from atlas.distributed.heartbeat import HeartbeatMonitor
from atlas.distributed.node_registry import NodeRegistry


def create_detector(timeout=0.02):
    registry = NodeRegistry(["node-1", "node-2"])
    monitor = HeartbeatMonitor(timeout_seconds=timeout)
    return FailureDetector(registry, monitor), registry


def test_heartbeat_keeps_node_available():
    detector, registry = create_detector()
    detector.heartbeat("node-1")
    assert detector.is_available("node-1")
    assert registry.is_available("node-1")


def test_missing_heartbeat_marks_node_failed():
    detector, registry = create_detector()
    detector.heartbeat("node-1")
    time.sleep(0.04)
    detector.check_nodes()
    assert not registry.is_available("node-1")


def test_new_heartbeat_recovers_failed_node():
    detector, registry = create_detector()
    detector.heartbeat("node-1")
    time.sleep(0.04)
    detector.check_nodes()

    detector.heartbeat("node-1")
    assert registry.is_available("node-1")


def test_failed_nodes_are_reported():
    detector, _ = create_detector()
    detector.heartbeat("node-1")
    time.sleep(0.04)
    assert detector.check_nodes() == ["node-1"]
