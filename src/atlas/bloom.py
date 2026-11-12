
from __future__ import annotations

import hashlib
import math


class BloomFilter:
    """Space-efficient probabilistic membership filter."""

    def __init__(
        self,
        capacity: int = 1000,
        false_positive_rate: float = 0.01,
    ):
        if not isinstance(capacity, int) or isinstance(capacity, bool):
            raise TypeError("Capacity must be an integer")

        if capacity <= 0:
            raise ValueError("Capacity must be positive")

        if not 0 < false_positive_rate < 1:
            raise ValueError("False positive rate must be between 0 and 1")

        self.capacity = capacity
        self.false_positive_rate = false_positive_rate

        self.bit_count = max(
            1,
            math.ceil(
                -capacity * math.log(false_positive_rate)
                / (math.log(2) ** 2)
            ),
        )

        self.hash_count = max(
            1,
            round((self.bit_count / capacity) * math.log(2)),
        )

        self._bits = 0
        self._items_added = 0

    @staticmethod
    def _validate_item(item: str) -> None:
        if not isinstance(item, str):
            raise TypeError("Bloom Filter items must be strings")

    def _positions(self, item: str):
        digest = hashlib.blake2b(
            item.encode("utf-8"),
            digest_size=16,
        ).digest()

        first = int.from_bytes(digest[:8], "big")
        second = int.from_bytes(digest[8:], "big")

        second |= 1

        for index in range(self.hash_count):
            yield (first + index * second) % self.bit_count

    def add(self, item: str) -> None:
        """Add an item to the filter."""
        self._validate_item(item)

        for position in self._positions(item):
            self._bits |= 1 << position

        self._items_added += 1

    def might_contain(self, item: str) -> bool:
        """Return False if absent, otherwise possibly True."""
        self._validate_item(item)

        return all(
            self._bits & (1 << position)
            for position in self._positions(item)
        )

    def __contains__(self, item: str) -> bool:
        return self.might_contain(item)

    def __len__(self) -> int:
        return self._items_added

    @property
    def estimated_false_positive_rate(self) -> float:
        """Estimate the current false positive probability."""
        return (
            1 - math.exp(
                -self.hash_count * self._items_added / self.bit_count
            )
        ) ** self.hash_count
