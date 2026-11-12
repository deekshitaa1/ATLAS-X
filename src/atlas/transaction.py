from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

if TYPE_CHECKING:
    from atlas.lsm import LSMTree


class Transaction:
    """Stage operations and commit or discard them together."""

    def __init__(self, database: LSMTree) -> None:
        self._database = database
        self._operations: list[tuple] = []
        self._active = True

    def _ensure_active(self) -> None:
        if not self._active:
            raise RuntimeError("Transaction is no longer active")

    def put(self, key: str, value: Any) -> None:
        self._ensure_active()
        self._operations.append(("put", key, value))

    def delete(self, key: str) -> None:
        self._ensure_active()
        self._operations.append(("delete", key))

    def get(self, key: str) -> Any | None:
        self._ensure_active()

        for operation in reversed(self._operations):
            if operation[1] == key:
                if operation[0] == "delete":
                    return None
                return operation[2]

        return self._database.get(key)

    def commit(self) -> None:
        self._ensure_active()
        self._database.batch(self._operations)
        self._active = False

    def rollback(self) -> None:
        self._ensure_active()
        self._operations.clear()
        self._active = False

    def __enter__(self) -> Self:
        self._ensure_active()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
