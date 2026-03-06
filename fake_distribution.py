# fake_distribution.py
"""
Generates fake replica accesses to pad batches.
Uses weighted sampling so that each replica is observed with approximately
equal probability (through fake accesses).
"""

from crypto_utils import make_replica_label
from replication_manager import ReplicationManager
import random


class FakeDistributionManager:
    """Generates fake replica accesses with smoothing so replica observations are balanced."""

    def __init__(self, replication_manager: ReplicationManager, batch_size = 3) -> None:
        self._replication_manager = replication_manager
        self._batch_size = batch_size

    def _all_replicas(self) -> list[tuple[str, int]]:
        """Returns a list of all (key, replica_id) pairs currently present."""
        replicas = []
        replication_factors = self._replication_manager.get_all_replication_factors()
        for key, R in replication_factors.items():
            for replica_id in range(R):
                replicas.append((key, replica_id))
        return replicas

    def _get_weighted_replicas(self) -> tuple[ list[tuple[str,int]], list[float] ]:
        """
        Returns (replicas, weights). Each weight for the replica is 
        the normalized fake-access probability that allows each replica
        to be seen with equal probability when real access count is included.
        Returns empty lists tuple if no replicas.
        """
        
        replicas = self._all_replicas()
        if not replicas:
            return [], []

        # 1/B queries of the batch are real
        # delta is the probability of the access being real
        # 1-delta is the probability of the access being fake
        delta = 1.0 / self._batch_size 
        pi = self._replication_manager.get_distribution() 
        replication_factors = self._replication_manager.get_all_replication_factors() 
        N = len(replicas) # number of real replicas

        raw_weights = []
        for key, _ in replicas:
            rf_k = replication_factors[key]
            pi_k = pi.get(key, 0.0)
            # (delta*(π(k)/R(k))) is the probability that a real request accesses the replica
            # ((1-delta)*π_f(k,j)) is the probability that a fake request accesses the replica
            # For uniformity, we need total probability = 1/N
            # isolate π_f(k,j) to get the weight for each replica
            weight = (1/N - delta*(pi_k/rf_k)) / (1-delta)
            weight = max(0.0, weight) # weight can't be negative
            raw_weights.append(weight)

        total = sum(raw_weights)
        return replicas, [weight/total for weight in raw_weights] # Normalized

    def get_fake_distribution(self) -> tuple[list[tuple[str, int]], list[float]]:
        """Return (replicas, weights) for the current fake distribution (testing func)."""
        return self._get_weighted_replicas()

    def sample_fake_replica(self) -> tuple[str, int]:
        """Sample 1 replica based on the smoothed fake distribution."""
        replicas, weights = self._get_weighted_replicas()
        if not replicas:
            raise RuntimeError("No replicas available for fake sampling")
        return random.choices(replicas, weights=weights, k=1)[0]

    def sample_fake_label(self) -> bytes:
        """Return the storage label for a sampled fake replica."""
        key, replica_id = self.sample_fake_replica()
        return make_replica_label(key, replica_id)