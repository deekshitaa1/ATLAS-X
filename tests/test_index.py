
import pytest

from atlas.index import HashIndex


def test_insert_and_search():
    index = HashIndex()
    index.insert("name", "Atlas")

    assert index.search("name") == "Atlas"


def test_update_existing_key():
    index = HashIndex()
    index.insert("version", 1)
    index.insert("version", 2)

    assert index.search("version") == 2


def test_delete_existing_key():
    index = HashIndex()
    index.insert("name", "Atlas")

    assert index.delete("name") is True
    assert index.search("name") is None


def test_delete_missing_key():
    index = HashIndex()

    assert index.delete("missing") is False


def test_contains():
    index = HashIndex()
    index.insert("active", True)

    assert index.contains("active")
    assert not index.contains("missing")


def test_scan():
    index = HashIndex()
    index.insert("a", 1)
    index.insert("b", 2)

    assert index.scan() == {"a": 1, "b": 2}


def test_length():
    index = HashIndex()
    index.insert("a", 1)
    index.insert("b", 2)

    assert len(index) == 2


def test_invalid_key():
    index = HashIndex()

    with pytest.raises(ValueError):
        index.insert("", "invalid")

    with pytest.raises(TypeError):
        index.search(123)

