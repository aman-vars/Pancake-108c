# distribution_estimator.py
"""
Tracks observed key access frequency for selective replication.
"""

from typing import Dict


class DistributionEstimator:
    """
    Tracks key -> access count. Increment on every logical GET or PUT.
    Provides normalized frequency π(k) and total_accesses().
    """

    def __init__(self) -> None:
        self._counts: Dict[str, int] = {}

    def record_access(self, key: str) -> None:
        """Record 1 access for given key."""
        self._counts[key] = self._counts.get(key, 0) + 1

    def get_distribution(self) -> Dict[str, float]:
        """
        Returns normalized frequency π(k): key -> probability.
        Sums to 1 over all keys. Empty if no accesses recorded.
        """
        total = self.total_accesses()
        if total == 0:
            return {}
        return {k: v / total for k, v in self._counts.items()}

    def total_accesses(self) -> int:
        """Total number of operations recorded."""
        return sum(self._counts.values())
