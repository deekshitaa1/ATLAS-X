import pytest

from atlas.distributed.quorum import QuorumConfig


def test_valid_quorum_configuration():
    config = QuorumConfig(replicas=3, read_quorum=2, write_quorum=2)
    assert config.quorum_intersects


def test_majority_quorum_intersects():
    config = QuorumConfig(replicas=5, read_quorum=3, write_quorum=3)
    assert config.quorum_intersects


def test_non_intersecting_quorum():
    config = QuorumConfig(replicas=3, read_quorum=1, write_quorum=1)
    assert not config.quorum_intersects


def test_invalid_replica_count():
    with pytest.raises(ValueError):
        QuorumConfig(replicas=0, read_quorum=1, write_quorum=1)


def test_quorum_cannot_exceed_replicas():
    with pytest.raises(ValueError):
        QuorumConfig(replicas=3, read_quorum=4, write_quorum=2)


def test_boolean_quorum_values_rejected():
    with pytest.raises(TypeError):
        QuorumConfig(replicas=3, read_quorum=True, write_quorum=2)
