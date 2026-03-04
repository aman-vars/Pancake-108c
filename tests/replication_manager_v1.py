"""
Tests for ReplicationManager.
- Skewed distribution produces larger R(k) for hot keys.
- Cold keys produce replication factor 1.
- total_real_replicas() equals sum of R(k).
"""

import sys
sys.path.insert(0, ".") # Removes PYTHONPATH reliance
from distribution_estimator import DistributionEstimator
from replication_manager import ReplicationManager


def main() -> None:
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
    assert factors["a"] == 3, "hot key 'a' should have replication factor > 1 (specifically 3)"
    assert factors["b"] == 1, "key 'b' should have R=1"
    assert factors["c"] == 1, "cold key 'c' should have R=1"
    
    # Ensure total # of real replicas equals sum of R(k)
    total = manager.total_real_replicas()
    assert total == sum(factors.values()), "total_real_replicas must equal sum R(k)"

    # Replication factor per key
    assert manager.get_replication_factor("a") == factors["a"]
    assert manager.get_replication_factor("b") == 1
    assert manager.get_replication_factor("unused") == 0

    print("ReplicationManager: all checks passed.")


if __name__ == "__main__":
    main()
