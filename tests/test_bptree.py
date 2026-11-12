
import pytest

from atlas.bptree import BPlusTree


def test_insert_and_search():
    tree = BPlusTree()

    tree.insert("apple", 10)
    tree.insert("banana", 20)

    assert tree.search("apple") == 10
    assert tree.search("banana") == 20


def test_missing_key():
    tree = BPlusTree()

    assert tree.search("missing") is None


def test_update_existing_key():
    tree = BPlusTree()

    tree.insert("version", 1)
    tree.insert("version", 2)

    assert tree.search("version") == 2
    assert len(tree) == 1


def test_node_splitting():
    tree = BPlusTree(max_keys=3)

    for number in range(30):
        tree.insert(f"key-{number:03}", number)

    assert tree.search("key-000") == 0
    assert tree.search("key-029") == 29
    assert tree.validate()


def test_sorted_scan():
    tree = BPlusTree()

    for key in ["d", "a", "c", "b"]:
        tree.insert(key, key.upper())

    assert list(tree.scan()) == ["a", "b", "c", "d"]


def test_range_scan():
    tree = BPlusTree()

    for number in range(10):
        tree.insert(f"k{number}", number)

    assert tree.scan("k3", "k7") == {
        "k3": 3,
        "k4": 4,
        "k5": 5,
        "k6": 6,
    }


def test_scan_limit():
    tree = BPlusTree()

    for number in range(10):
        tree.insert(f"k{number}", number)

    assert len(tree.scan(limit=3)) == 3


def test_delete():
    tree = BPlusTree()

    tree.insert("a", 1)
    tree.insert("b", 2)

    assert tree.delete("a") is True
    assert tree.delete("a") is False
    assert tree.search("a") is None
    assert tree.search("b") == 2


def test_leaf_links_after_splits():
    tree = BPlusTree(max_keys=3)

    for number in range(50):
        tree.insert(f"{number:03}", number)

    assert list(tree.scan()) == [
        f"{number:03}" for number in range(50)
    ]


def test_validation():
    tree = BPlusTree(max_keys=3)

    for number in range(100):
        tree.insert(f"{number:03}", number)

    assert tree.validate()


def test_invalid_key():
    tree = BPlusTree()

    with pytest.raises(ValueError):
        tree.insert("", 1)

    with pytest.raises(TypeError):
        tree.search(123)


def test_invalid_order():
    with pytest.raises(ValueError):
        BPlusTree(max_keys=2)


def test_invalid_limit():
    tree = BPlusTree()

    with pytest.raises(ValueError):
        tree.scan(limit=-1)
