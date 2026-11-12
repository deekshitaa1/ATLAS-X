
import pytest

from atlas.bloom import BloomFilter


def test_inserted_item_is_found():
    bloom = BloomFilter()

    bloom.add("atlas")

    assert bloom.might_contain("atlas")


def test_multiple_items_are_found():
    bloom = BloomFilter()

    items = ["apple", "banana", "cherry"]

    for item in items:
        bloom.add(item)

    for item in items:
        assert bloom.might_contain(item)


def test_missing_item_is_absent():
    bloom = BloomFilter()

    bloom.add("atlas")

    assert not bloom.might_contain("unknown")


def test_membership_operator():
    bloom = BloomFilter()
    bloom.add("database")

    assert "database" in bloom
    assert "missing" not in bloom


def test_item_count():
    bloom = BloomFilter()

    bloom.add("a")
    bloom.add("b")

    assert len(bloom) == 2


def test_invalid_capacity():
    with pytest.raises(ValueError):
        BloomFilter(capacity=0)


def test_invalid_capacity_type():
    with pytest.raises(TypeError):
        BloomFilter(capacity=1.5)


def test_invalid_false_positive_rate():
    with pytest.raises(ValueError):
        BloomFilter(false_positive_rate=1.0)


def test_non_string_item():
    bloom = BloomFilter()

    with pytest.raises(TypeError):
        bloom.add(123)


def test_inserted_items_never_false_negative():
    bloom = BloomFilter(capacity=1000)

    items = [f"key-{number}" for number in range(1000)]

    for item in items:
        bloom.add(item)

    assert all(bloom.might_contain(item) for item in items)


def test_estimated_false_positive_rate():
    bloom = BloomFilter(
        capacity=1000,
        false_positive_rate=0.01,
    )

    assert bloom.estimated_false_positive_rate == 0.0

    for number in range(1000):
        bloom.add(f"key-{number}")

    assert bloom.estimated_false_positive_rate <= 0.02
