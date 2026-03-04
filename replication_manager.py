# replication_manager.py
"""
Computes replication factors R(k) from
access distribution (using DistributionEstimator).
Total replicas is 2n; dummy replicas pad to 2n.
"""

import math
from typing import Dict
from distribution_estimator import DistributionEstimator


class ReplicationManager:
    """
    Given a DistributionEstimator, computes per-key replication factor:
    n = # of distinct keys, alpha = 1/n, R(k) = ceil(π'(k) / alpha).
    Total replicas = 2n; dummy replicas = 2n - real replicas.
    """

    def __init__(self, estimator: DistributionEstimator) -> None:
        self._estimator = estimator

    def get_total_replica_target(self) -> int:
        """Total number of replicas the server should store: 2n."""
        return 2 * self._estimator.num_keys()

    def get_dummy_replica_count(self) -> int:
        """
        Number of dummy replicas (for dummy key D) needed so that
        total_real_replicas + dummy_replicas == 2n.
        """
        target = self.get_total_replica_target()
        real = self.total_real_replicas()
        return max(0, target - real)

    def get_replication_factor(self, key: str) -> int:
        """Replication factor for key. 0 if key was never observed."""
        factors = self.get_all_replication_factors()
        return factors.get(key, 0)

    def get_all_replication_factors(self) -> Dict[str, int]:
        """
        R(k) = ceil(π'(k) / alpha) for each key, with n = # of distinct keys, alpha = 1/n.
        Empty if no keys observed.
        """
        
        pi = self._estimator.get_distribution()
        n = len(pi) # Same as num_keys()
        if n == 0:
            return {}
        alpha = 1.0 / n
        return {k: max(1, math.ceil(pik / alpha)) for k, pik in pi.items()}

    def total_real_replicas(self) -> int:
        """Sum of R(k) over all keys."""
        return sum(self.get_all_replication_factors().values())
