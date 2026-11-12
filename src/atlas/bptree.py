
from __future__ import annotations

from bisect import bisect_left, bisect_right
from dataclasses import dataclass, field
from typing import Any


@dataclass
class _Node:
    leaf: bool
    keys: list[str] = field(default_factory=list)
    values: list[Any] = field(default_factory=list)
    children: list[_Node] = field(default_factory=list)
    next: _Node | None = None


class BPlusTree:
    """
    In-memory B+ Tree.

    All values are stored in leaf nodes.
    Internal nodes contain separator keys.
    Leaf nodes are linked for efficient range scans.
    """

    def __init__(self, max_keys: int = 4):
        if not isinstance(max_keys, int) or isinstance(max_keys, bool):
            raise TypeError("max_keys must be an integer")

        if max_keys < 3:
            raise ValueError("max_keys must be at least 3")

        self.max_keys = max_keys
        self.root = _Node(leaf=True)
        self._size = 0

    @staticmethod
    def _validate_key(key: str) -> None:
        if not isinstance(key, str):
            raise TypeError("Key must be a string")

        if not key:
            raise ValueError("Key cannot be empty")

    def _find_leaf(self, key: str) -> _Node:
        node = self.root

        while not node.leaf:
            position = bisect_right(node.keys, key)
            node = node.children[position]

        return node

    def search(self, key: str) -> Any | None:
        self._validate_key(key)

        leaf = self._find_leaf(key)
        position = bisect_left(leaf.keys, key)

        if position < len(leaf.keys) and leaf.keys[position] == key:
            return leaf.values[position]

        return None

    def contains(self, key: str) -> bool:
        self._validate_key(key)

        leaf = self._find_leaf(key)
        position = bisect_left(leaf.keys, key)

        return (
            position < len(leaf.keys)
            and leaf.keys[position] == key
        )

    def insert(self, key: str, value: Any) -> None:
        self._validate_key(key)

        separator = self._insert_recursive(self.root, key, value)

        if separator is not None:
            split_key, right_node = separator

            self.root = _Node(
                leaf=False,
                keys=[split_key],
                children=[self.root, right_node],
            )

    def _insert_recursive(
        self,
        node: _Node,
        key: str,
        value: Any,
    ) -> tuple[str, _Node] | None:

        if node.leaf:
            position = bisect_left(node.keys, key)

            if position < len(node.keys) and node.keys[position] == key:
                node.values[position] = value
                return None

            node.keys.insert(position, key)
            node.values.insert(position, value)
            self._size += 1

            if len(node.keys) <= self.max_keys:
                return None

            middle = len(node.keys) // 2

            right = _Node(
                leaf=True,
                keys=node.keys[middle:],
                values=node.values[middle:],
                next=node.next,
            )

            node.keys = node.keys[:middle]
            node.values = node.values[:middle]
            node.next = right

            return right.keys[0], right

        position = bisect_right(node.keys, key)
        split = self._insert_recursive(
            node.children[position],
            key,
            value,
        )

        if split is None:
            return None

        split_key, right_child = split

        node.keys.insert(position, split_key)
        node.children.insert(position + 1, right_child)

        if len(node.keys) <= self.max_keys:
            return None

        middle = len(node.keys) // 2
        promoted_key = node.keys[middle]

        right = _Node(
            leaf=False,
            keys=node.keys[middle + 1:],
            children=node.children[middle + 1:],
        )

        node.keys = node.keys[:middle]
        node.children = node.children[:middle + 1]

        return promoted_key, right

    def delete(self, key: str) -> bool:
        """
        Delete a key from a leaf.

        This initial version does not rebalance underfull nodes.
        """
        self._validate_key(key)

        leaf = self._find_leaf(key)
        position = bisect_left(leaf.keys, key)

        if position == len(leaf.keys) or leaf.keys[position] != key:
            return False

        leaf.keys.pop(position)
        leaf.values.pop(position)
        self._size -= 1

        return True

    def scan(
        self,
        start: str | None = None,
        end: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """
        Return sorted key-value pairs.

        start: inclusive lower bound.
        end: exclusive upper bound.
        limit: maximum number of results.
        """
        if start is not None:
            self._validate_key(start)

        if end is not None:
            self._validate_key(end)

        if limit is not None:
            if not isinstance(limit, int) or isinstance(limit, bool):
                raise TypeError("limit must be an integer")

            if limit < 0:
                raise ValueError("limit cannot be negative")

        if limit == 0 or (start is not None and end is not None and start >= end):
            return {}

        node = (
            self._find_leaf(start)
            if start is not None
            else self._leftmost_leaf()
        )

        result: dict[str, Any] = {}

        while node is not None:
            position = (
                bisect_left(node.keys, start)
                if start is not None
                else 0
            )

            for index in range(position, len(node.keys)):
                key = node.keys[index]

                if end is not None and key >= end:
                    return result

                result[key] = node.values[index]

                if limit is not None and len(result) >= limit:
                    return result

            node = node.next

        return result

    def _leftmost_leaf(self) -> _Node:
        node = self.root

        while not node.leaf:
            node = node.children[0]

        return node

    def __len__(self) -> int:
        return self._size

    def validate(self) -> bool:
        """Check ordering, node sizes, child counts and leaf links."""
        leaves: list[_Node] = []

        def visit(node: _Node, is_root: bool = False) -> tuple[str, str]:
            if node.keys != sorted(node.keys):
                raise AssertionError("Node keys are not sorted")

            if len(node.keys) > self.max_keys:
                raise AssertionError("Node exceeds maximum key count")

            if len(set(node.keys)) != len(node.keys):
                raise AssertionError("Duplicate keys in node")

            if not is_root and not node.keys:
                raise AssertionError("Empty non-root node")

            if node.leaf:
                if len(node.keys) != len(node.values):
                    raise AssertionError("Leaf keys/values mismatch")

                if node.children:
                    raise AssertionError("Leaf node has children")

                leaves.append(node)

                if not node.keys:
                    return "", ""

                return node.keys[0], node.keys[-1]

            if len(node.children) != len(node.keys) + 1:
                raise AssertionError("Internal child count mismatch")

            if not node.keys:
                raise AssertionError("Internal node has no separators")

            ranges = [
                visit(child)
                for child in node.children
            ]

            for index, separator in enumerate(node.keys):
                left_max = ranges[index][1]
                right_min = ranges[index + 1][0]

                if left_max >= separator:
                    raise AssertionError("Invalid left separator boundary")

                if right_min != separator:
                    raise AssertionError("Invalid right separator boundary")

            return ranges[0][0], ranges[-1][1]

        visit(self.root, is_root=True)

        total = 0

        for index, leaf in enumerate(leaves):
            expected_next = (
                leaves[index + 1]
                if index + 1 < len(leaves)
                else None
            )

            if leaf.next is not expected_next:
                raise AssertionError("Invalid leaf linked list")

            total += len(leaf.keys)

        if total != self._size:
            raise AssertionError("Tree size does not match leaf contents")

        return True
