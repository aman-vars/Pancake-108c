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
    Computes per-key replication factor: R(k) = ceil(π'(k) / alpha)
    where n = # of distinct keys and alpha = 1/n.
    Total replicas = 2n; dummy replicas = 2n - real replicas.
    """

    def __init__(self, estimator: DistributionEstimator) -> None:
        self._estimator = estimator

    def get_total_replica_target(self) -> int:
        """Total number of replicas the server should store: 2n."""
        return 2 * self._estimator.num_keys()

    def get_dummy_replica_count(self) -> int:
        """Returns number of dummy replicas needed so that total is 2n."""
        target = self.get_total_replica_target()
        real = self.total_real_replicas()
        return max(0, target - real)

    def get_replication_factor(self, key: str) -> int:
        """Return replication factor (R(k)) for key."""
        pi = self._estimator.get_distribution()
        n = len(pi) # Same as estimator.num_keys() 
        if key not in pi: # Key not found
            return 0 
        alpha = 1.0/n
        return max( 1, math.ceil(pi[key]/alpha) )

    def get_all_replication_factors(self) -> Dict[str, int]:
        """Return replication factor (R(k)) for all keys."""
        pi = self._estimator.get_distribution()
        return {k : self.get_replication_factor(k) for k in pi}

    def total_real_replicas(self) -> int:
        """Sum of R(k) over all keys."""
        return sum(self.get_all_replication_factors().values())
