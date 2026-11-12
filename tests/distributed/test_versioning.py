import pytest

from atlas.distributed.versioning import VersionClock, VersionedValue


def test_version_clock_increments():
    clock = VersionClock()
    assert clock.next_version() == 1
    assert clock.next_version() == 2
    assert clock.next_version() == 3


def test_current_version():
    clock = VersionClock()
    clock.next_version()
    assert clock.current == 1


def test_versioned_value_stores_data():
    entry = VersionedValue(version=1, value="ATLAS-X")
    assert entry.version == 1
    assert entry.value == "ATLAS-X"


def test_zero_version_rejected():
    with pytest.raises(ValueError):
        VersionedValue(version=0, value="data")


def test_boolean_version_rejected():
    with pytest.raises(TypeError):
        VersionedValue(version=True, value="data")
