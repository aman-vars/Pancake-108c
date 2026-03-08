# tests/fake_distribution_test.py
"""
Tests for fake distribution sampling.
- Only existing replicas are allowed to be sampled.
- Fake labels must be valid.
- Instance when no replicas available
- With dummy_replica_manager, dummy replicas are included and N=2n.
"""

import sys
sys.path.insert(0, ".")
from crypto_utils import LABEL_LENGTH, make_replica_label
from distribution_estimator import DistributionEstimator
from replication_manager import ReplicationManager
from fake_distribution import FakeDistributionManager
from dummy_replica_manager import DUMMY_KEY, DummyReplicaManager
from server import Server


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
        pass
    else:
        raise AssertionError("Expected RuntimeError when no replicas exist")

    # 4
    # Include dummy replicas in fake distribution sampling 
    server = Server()
    est4 = DistributionEstimator()
    est4.record_access("x")
    est4.record_access("y")
    rm4 = ReplicationManager(est4)
    dummy_mgr = DummyReplicaManager(server, rm4)
    dummy_mgr.rebalance()
    fdm4 = FakeDistributionManager(rm4, batch_size=3, dummy_replica_manager=dummy_mgr)
    replicas4, weights4 = fdm4.get_fake_distribution()
    assert len(replicas4) == rm4.get_total_replica_target()
    assert sum(weights4) - 1.0 < 1e-6
    dummy_replicas = [(k, r) for k, r in replicas4 if k == DUMMY_KEY]
    real_replicas = [(k, r) for k, r in replicas4 if k != DUMMY_KEY]
    assert len(dummy_replicas) == rm4.get_dummy_replica_count()
    assert len(dummy_replicas) + len(real_replicas) == len(replicas4)
    sampled_keys = set()
    for _ in range(200):
        key, _ = fdm4.sample_fake_replica()
        sampled_keys.add(key)
    assert DUMMY_KEY in sampled_keys, "dummy replicas should be sampled when in fake distribution"

    print("Fake Distribution Manager: All tests passed.")



if __name__ == "__main__":
    main()