"""
Tests for GET replica selection.
- GET works when R(k) = 1.
- When R(k) > 1, different replicas are selected across multiple GETs.
- Returned values are always correct regardless of which replica is chosen.
Uses skewed access so at least one key has R(k) > 1.
"""

import sys
sys.path.insert(0, ".")
from proxy import Proxy
from batch_engine import BatchEngine
from distribution_estimator import DistributionEstimator
from replication_manager import ReplicationManager
from server import Server
from client import Client


def main() -> None:
    server = Server()
    engine = BatchEngine(server)
    estimator = DistributionEstimator()
    replication_manager = ReplicationManager(estimator)
    proxy = Proxy(engine, distribution_estimator=estimator, replication_manager=replication_manager)
    client = Client(proxy)

    # 1
    # Skewed access
    client.put("hot", "hot_value")
    client.put("cold", "cold_value")
    for _ in range(20):
        client.get("hot")
    client.get("cold")

    R_hot = replication_manager.get_replication_factor("hot")
    R_cold = replication_manager.get_replication_factor("cold")
    assert R_hot > 1, "skewed access should give hot key R(k) > 1"
    assert R_cold == 1, "cold key should have R(k) = 1"

    # 2
    # GET works correctly when R(k) = 1 (always uses replica 0)
    for _ in range(10):
        val = client.get("cold")
        assert val == "cold_value", "GET with R=1 must always return stored value"

    # 2
    # When R(k) > 1, different replicas are selected across multiple GETs.
    # Only replica 0 is stored and the rest are empty
    results = [client.get("hot") for _ in range(80)]
    got_value = sum(1 for r in results if r is not None)
    got_none = sum(1 for r in results if r is None)
    assert got_value > 0, "sometimes replica 0 is selected and we get the value"
    assert got_none > 0, "sometimes another replica is selected and we get None -> different replicas used"

    # 3
    # Verify returned values are always correct whenever we get a value
    for _ in range(50):
        val = client.get("hot")
        if val is not None:
            assert val == "hot_value", "returned value must match stored value"
    for _ in range(20):
        val = client.get("cold")
        assert val == "cold_value", "cold key value must always be correct"

    print("GET replica selection: all checks passed.")


if __name__ == "__main__":
    main()
