# fake_distribution.py
"""
Generates fake replica accesses to pad batches.
Uses weighted sampling so that each replica is observed with approximately
equal probability (through fake accesses). Includes dummy replicas 
so the distribution is over all 2n replicas.
"""

from crypto_utils import make_replica_label
from replication_manager import ReplicationManager
from dummy_replica_manager import DUMMY_KEY
import random
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from dummy_replica_manager import DummyReplicaManager


class FakeDistributionManager:
    """Generates fake replica accesses with smoothing so replica observations are balanced."""

    def __init__(self, replication_manager: ReplicationManager, batch_size = 3, dummy_replica_manager: Optional["DummyReplicaManager"] = None) -> None:
        self._replication_manager = replication_manager
        self._batch_size = batch_size
        self._dummy_replica_manager = dummy_replica_manager

    def _all_replicas(self) -> list[tuple[str, int]]:
        """Returns a list of all (key, replica_id) pairs (real and dummy)."""
        replicas = []
        replication_factors = self._replication_manager.get_all_replication_factors()
        for key, R in replication_factors.items():
            for replica_id in range(R):
                replicas.append((key, replica_id))
                
        # Append dummy replicas
        if self._dummy_replica_manager:
            dummy_count = self._replication_manager.get_dummy_replica_count()
            dummy_ids = self._dummy_replica_manager.get_dummy_replica_ids()
            for i in range(min(dummy_count, len(dummy_ids))):
                replicas.append((DUMMY_KEY, dummy_ids[i]))
        return replicas

    def _get_weighted_replicas(self) -> tuple[list[tuple[str, int]], list[float]]:
        """
        Returns (replicas, weights). Weights are fake-access probabilities so that
        each of the N total replicas (real + dummy) is accessed uniformly.
        N = 2n when dummy manager is set.
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
        if self._dummy_replica_manager:
            N = self._replication_manager.get_total_replica_target()
        else:
            N = len(replicas)

        raw_weights = []
        for key, _ in replicas: 
            if key != DUMMY_KEY: # Real 
                # (delta*(π(k)/R(k))) is the probability that a real request accesses the replica
                # ((1-delta)*π_f(k,j)) is the probability that a fake request accesses the replica 
                # For uniformity, we need total probability = 1/N 
                rf_k = replication_factors[key]
                pi_k = pi.get(key, 0.0)
                weight = (1.0 / N - delta * (pi_k / rf_k)) / (1.0 - delta)
                weight = max(0.0, weight)
            else: # Dummy
                # For dummy keys, π(k) = 0 so the smoothing formula is
                # 1/N = (1-delta) * π_f(k,j)  ->  π_f(k,j) = (1/N)/(1-delta)
                weight = (1/N) / (1-delta)
            raw_weights.append(weight)

        total = sum(raw_weights)
        total = 1.0 if total <= 0 else total # Set total to positive if negative
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