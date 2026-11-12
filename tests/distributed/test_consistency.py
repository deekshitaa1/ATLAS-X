import pytest

from atlas.distributed.consistency import ConsistencyChecker


def test_identical_replicas_are_consistent():
    checker = ConsistencyChecker()
    replicas = {
        "node-1": {"name": "Atlas", "version": 1},
        "node-2": {"name": "Atlas", "version": 1},
        "node-3": {"name": "Atlas", "version": 1},
    }
    assert checker.check(replicas)


def test_different_replicas_are_inconsistent():
    checker = ConsistencyChecker()
    replicas = {
        "node-1": "value-a",
        "node-2": "value-a",
        "node-3": "value-b",
    }
    assert not checker.check(replicas)


def test_find_outlier_replica():
    checker = ConsistencyChecker()
    replicas = {
        "node-1": "correct",
        "node-2": "correct",
        "node-3": "wrong",
    }
    assert checker.find_outliers(replicas) == ["node-3"]


def test_empty_replicas_are_consistent():
    checker = ConsistencyChecker()
    assert checker.check({})
    assert checker.find_outliers({}) == []


def test_dictionary_key_order_does_not_affect_consistency():
    checker = ConsistencyChecker()
    replicas = {
        "node-1": {"a": 1, "b": 2},
        "node-2": {"b": 2, "a": 1},
    }
    assert checker.check(replicas)


def test_non_json_value_is_rejected():
    checker = ConsistencyChecker()
    with pytest.raises((TypeError, ValueError)):
        checker.check({"node-1": float("nan")})
