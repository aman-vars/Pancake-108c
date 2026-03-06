# tests/fake_distribution_smoothing_test.py
"""
Tests for the fake distribution smoothing.
- Fake probabilities (weights) are valid (non-negative, each replica present).
- Weights sum to approximately 1.
- Weighted sampling produces expected behavior over many trials.
"""

import sys
sys.path.insert(0, ".")
from distribution_estimator import DistributionEstimator
from replication_manager import ReplicationManager
from fake_distribution import FakeDistributionManager


def main():
    # 1
    # Weights are non-negative, one per replica, and sum to ~1
    estimator = DistributionEstimator()
    for _ in range(10):
        estimator.record_access("a")
    for _ in range(10):
        estimator.record_access("b")

    rm = ReplicationManager(estimator)
    fdm = FakeDistributionManager(rm, batch_size=3)

    replicas, weights = fdm.get_fake_distribution()

    assert len(replicas) == len(weights), "one weight per replica"
    assert len(replicas) > 0, "should have replicas"

    for w in weights:
        assert w >= 0.0, "weights must be non-negative"
        assert w <= 1, "weights cannot be greater than 1"

    total = sum(weights)
    assert abs(total - 1.0) < 1e-6, f"weights should sum to 1, got {total}"

    # 2
    # With one key, weights still sum to 1
    estimator2 = DistributionEstimator()
    for _ in range(5):
        estimator2.record_access("only")

    rm2 = ReplicationManager(estimator2)
    fdm2 = FakeDistributionManager(rm2, batch_size=3)

    replicas2, weights2 = fdm2.get_fake_distribution()
    assert len(replicas2) >= 1
    assert abs(sum(weights2) - 1.0) < 1e-6
    
    # 3
    # Weighted sampling should only returns replicas that exist in distribution
    estimator3 = DistributionEstimator()
    for _ in range(7):
        estimator3.record_access("x")
    for _ in range(3):
        estimator3.record_access("y")

    rm3 = ReplicationManager(estimator3)
    fdm3 = FakeDistributionManager(rm3, batch_size=3)
    factors3 = rm3.get_all_replication_factors()

    for _ in range(200):
        key3, replica_id3 = fdm3.sample_fake_replica()
        assert key3 in factors3
        assert 0 <= replica_id3 < factors3[key3]
        
    # 4 
    # with skewed π, replicas of low π keys should get higher fake weight and be sampled more
    estimator4 = DistributionEstimator()
    for _ in range(90):
        estimator4.record_access("hot")
    for _ in range(10):
        estimator4.record_access("cold")

    rm4 = ReplicationManager(estimator4)
    fdm4 = FakeDistributionManager(rm4, batch_size=3)
    replicas4, weights4 = fdm4.get_fake_distribution()

    # Build expected: (key, replica_id) -> weight
    replica_to_weight = {r: w for r, w in zip(replicas4, weights4)}

    # Cold replicas should have higher fake weight than hot
    cold_replicas = [(k, j) for k, j in replicas4 if k == "cold"]
    hot_replicas = [(k, j) for k, j in replicas4 if k == "hot"]
    assert cold_replicas and hot_replicas

    avg_cold_weight = sum(replica_to_weight[r] for r in cold_replicas) / len(cold_replicas)
    avg_hot_weight = sum(replica_to_weight[r] for r in hot_replicas) / len(hot_replicas)

    # Cold should have higher fake weight
    assert avg_cold_weight > avg_hot_weight, (
        "cold replicas should have higher fake weight than hot"
    )

    # Over many trials, cold keys should appear more often
    cold_count = 0
    n_trials = 2000
    for _ in range(n_trials):
        key, _ = fdm4.sample_fake_replica()
        if key == "cold":
            cold_count += 1

    # For uniformity over replicas, cold would be len(cold_replicas)/len(replicas)
    # For smoothing, cold should be sampled more
    uniform_fraction = len(cold_replicas) / len(replicas4)
    observed_fraction = cold_count / n_trials
    assert observed_fraction >= uniform_fraction * 0.8, (
        f"expected cold to be sampled at least ~uniform rate: "
        f"observed {observed_fraction:.3f}, uniform ~{uniform_fraction:.3f}"
    )
    
    
    print("Fake distribution smoothing: all tests passed.")
    
    
    
if __name__ == "__main__":
    main()
