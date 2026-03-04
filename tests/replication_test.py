# tests/replication_manager_v1.py
"""
Tests for ReplicationManager.
- Skewed distribution produces larger R(k) for hot keys.
- Cold keys produce replication factor 1.
- total_real_replicas() equals sum of R(k).
- Dummy replica count: real + dummy == 2n, dummy ≥ 0.
"""

import sys
sys.path.insert(0, ".") # Removes PYTHONPATH reliance
from distribution_estimator import DistributionEstimator
from replication_manager import ReplicationManager


def test_basic_replication_factors() -> None:
    """Skewed distribution, R(k) sum, per-key factor."""
    estimator = DistributionEstimator()
    # Access skew: a hot, b warm, c cold 
    for _ in range(10):
        estimator.record_access("a")
    for _ in range(3):
        estimator.record_access("b")
    estimator.record_access("c")

    manager = ReplicationManager(estimator)
    factors = manager.get_all_replication_factors()

    # n = 3, alpha = 1/3. π'(a)=10/14, π'(b)=3/14, π'(c)=1/14.
    # R(a)=ceil((10/14)/(1/3))=ceil(30/14)=3, R(b)=ceil((3/14)/(1/3))=ceil(9/14)=1, R(c)=ceil((1/14)/(1/3))=1
    assert factors["a"] == 3
    assert factors["b"] == 1
    assert factors["c"] == 1
    total = manager.total_real_replicas()
    assert total == sum(factors.values())
    assert manager.get_replication_factor("a") == 3
    assert manager.get_replication_factor("unused") == 0


def test_dummy_replicas() -> None:
    """
    real + dummy == 2n; 
    Dummy should never be negative; 
    Dummy should adjust with distribution.
    """
    
    # 1
    # Small uniform distribution
    # n=2, 2n=4. Each key R=1 -> real=2, dummy=2.
    est = DistributionEstimator()
    est.record_access("x")
    est.record_access("y")
    mgr = ReplicationManager(est)
    n = 2
    target = mgr.get_total_replica_target()
    assert target == 2 * n
    real = mgr.total_real_replicas()
    dummy = mgr.get_dummy_replica_count()
    assert real + dummy == 2 * n, "real + dummy must equal 2n"
    assert dummy >= 0, "dummy count can't be negative"
    assert dummy == 2, "2 keys, 2 real -> dummy = 4 - 2 = 2"

    # 2
    # Skewed
    # Many accesses to one key so # of real can hit 2n.
    est2 = DistributionEstimator()
    for _ in range(100):
        est2.record_access("hot")
    est2.record_access("cold")
    mgr2 = ReplicationManager(est2)
    n2 = 2
    real2 = mgr2.total_real_replicas()
    dummy2 = mgr2.get_dummy_replica_count()
    assert real2 + dummy2 == 2 * n2
    assert dummy2 >= 0
    # dummy2 = 4 - real2 (or 0 if real2 >= 4).
    assert mgr2.get_dummy_replica_count() == max(0, 4 - real2)
    
    # 3
    # Small non-uniform distribution 
    # (n=1): 2n=2, real=1, dummy=1
    est_small = DistributionEstimator()
    est_small.record_access("only")
    mgr_small = ReplicationManager(est_small)
    assert mgr_small.get_total_replica_target() == 2
    assert mgr_small.total_real_replicas() == 1
    assert mgr_small.get_dummy_replica_count() == 1
    assert mgr_small.total_real_replicas() + mgr_small.get_dummy_replica_count() == 2
    assert mgr_small.get_dummy_replica_count() >= 0


def main() -> None:
    test_basic_replication_factors()
    test_dummy_replicas()
    print("ReplicationManager: all checks passed.")


if __name__ == "__main__":
    main()
