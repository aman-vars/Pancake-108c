# tests/fake_distribution_test.py
"""
Tests for fake distribution sampling.
- Only existing replicas are allowed to be sampled.
- Fake labels must be valid.
- Instance when no replicas available
"""

import sys
sys.path.insert(0, ".")
from crypto_utils import LABEL_LENGTH, make_replica_label
from distribution_estimator import DistributionEstimator
from replication_manager import ReplicationManager
from fake_distribution import FakeDistributionManager


def main():
    # 1
    # Fake distribution should sample only existing replicas
    estimator = DistributionEstimator()
    for _ in range(10):
        estimator.record_access("a")
    for _ in range(5):
        estimator.record_access("b")

    rm = ReplicationManager(estimator)
    fdm = FakeDistributionManager(rm)

    replicas = set()
    for _ in range(100):
        key, replica_id = fdm.sample_fake_replica()
        replicas.add((key, replica_id))

    # verify replicas correspond to real keys
    factors = rm.get_all_replication_factors()
    for key, rid in replicas:
        assert key in factors
        assert 0 <= rid < factors[key]
        
    
    # 2
    # Fake labels should be valid PRF labels (fixed length, and one of the replica labels)
    estimator2 = DistributionEstimator()
    for _ in range(10):
        estimator2.record_access("user")

    rm2 = ReplicationManager(estimator2)
    fdm2 = FakeDistributionManager(rm2)

    label = fdm2.sample_fake_label()

    assert isinstance(label, bytes)
    assert len(label) == LABEL_LENGTH
    factors2 = rm2.get_all_replication_factors()
    valid_labels = {make_replica_label(k, rid) for k, R in factors2.items() for rid in range(R)}
    assert label in valid_labels
    
    
    # 3
    # Verify system fails when no replicas exist
    estimator3 = DistributionEstimator()
    rm3 = ReplicationManager(estimator3)
    fdm3 = FakeDistributionManager(rm3)

    try:
        fdm3.sample_fake_replica()
    except RuntimeError:
        print("Fake Distribution Manager: All tests passed.")
        return

    raise AssertionError("Expected RuntimeError when no replicas exist")



if __name__ == "__main__":
    main()