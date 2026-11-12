from __future__ import annotations


class QuorumConfig:
    """Configure read and write quorum requirements."""

    def __init__(self, replicas: int, read_quorum: int, write_quorum: int):
        values = (replicas, read_quorum, write_quorum)

        if any(not isinstance(value, int) or isinstance(value, bool) for value in values):
            raise TypeError("Quorum values must be integers")

        if replicas <= 0:
            raise ValueError("replicas must be positive")

        if not 1 <= read_quorum <= replicas:
            raise ValueError("read_quorum must be between 1 and replicas")

        if not 1 <= write_quorum <= replicas:
            raise ValueError("write_quorum must be between 1 and replicas")

        self.replicas = replicas
        self.read_quorum = read_quorum
        self.write_quorum = write_quorum

    @property
    def quorum_intersects(self) -> bool:
        return self.read_quorum + self.write_quorum > self.replicas
