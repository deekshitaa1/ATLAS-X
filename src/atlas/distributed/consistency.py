from __future__ import annotations

import hashlib
import json
from typing import Any


class ConsistencyChecker:
    """Compare replicated values and detect inconsistent replicas."""

    @staticmethod
    def _digest(value: Any) -> str:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def check(self, replicas: dict[str, Any]) -> bool:
        if not replicas:
            return True

        digests = {
            self._digest(value)
            for value in replicas.values()
        }
        return len(digests) == 1

    def find_outliers(self, replicas: dict[str, Any]) -> list[str]:
        if not replicas:
            return []

        counts: dict[str, int] = {}
        for value in replicas.values():
            digest = self._digest(value)
            counts[digest] = counts.get(digest, 0) + 1

        majority = max(counts, key=counts.get)

        return [
            node
            for node, value in replicas.items()
            if self._digest(value) != majority
        ]
