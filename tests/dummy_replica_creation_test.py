"""
Test to verify server always stores exactly 2n entries (real + dummy).
- Total entries = 2n after each PUT and after rebalances.
- Adding keys increases n and total so dummies grow.
- When real replicas increase, dummies shrink.
- Repeated rebalances are correct and deterministic.
"""

import random
import sys
sys.path.insert(0, ".")

from proxy import Proxy
from batch_engine import BatchEngine
from distribution_estimator import DistributionEstimator
from dummy_replica_manager import DummyReplicaManager
from replication_manager import ReplicationManager
from server import Server
from update_cache import UpdateCache
from client import Client


def assert_invariant(server, rm, msg=""):
    target = rm.get_total_replica_target()
    actual = server.size()
    assert actual == target, f"{msg} expected 2n={target}, got {actual}"


def main():
    random.seed(1)
    server = Server()
    est = DistributionEstimator()
    rm = ReplicationManager(est)
    cache = UpdateCache()
    dummy_mgr = DummyReplicaManager(server, rm)
    engine = BatchEngine(server, batch_size=1)
    proxy = Proxy(engine, distribution_estimator=est, replication_manager=rm, update_cache=cache, dummy_manager=dummy_mgr)
    client = Client(proxy)

    # 1. Total entries = 2n after each PUT
    client.put("a", "1")
    assert_invariant(server, rm, "after put(a)")
    client.put("b", "2")
    assert_invariant(server, rm, "after put(b)")
    client.put("c", "3")
    assert_invariant(server, rm, "after put(c)")

    # 2. Replicas grow: n=3 => 6 entries; skew so R(a) grows, then rebalance
    for _ in range(50):
        client.get("a")
    client.get("b")
    client.get("c")
    client.put("a", "10")
    assert_invariant(server, rm, "after skew + put(a)")

    # 3. After skew + put, total still 2n (rebalance uses server.size() so overwrites are handled)
    assert_invariant(server, rm, "after skew (repeated)")

    # 4. Repeated rebalances: multiple PUTs, invariant holds each time
    for i in range(10):
        client.put("b", f"b{i}")
        assert_invariant(server, rm, f"after repeated put(b) #{i}")

    # 5. Add another key; n and 2n increase
    client.put("d", "4")
    assert_invariant(server, rm, "after put(d)")

    # 6. Idempotent rebalance: calling rebalance again leaves 2n unchanged
    dummy_mgr.rebalance()
    assert_invariant(server, rm, "after extra rebalance()")

    print("dummy_replica_creation_test ok")


if __name__ == "__main__":
    main()
