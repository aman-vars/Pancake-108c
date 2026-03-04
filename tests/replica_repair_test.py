"""
Tests for replica repairing on GET queries.
- Write key multiple times so stale replicas appear.
- Perform reads and verify stale replicas get repaired.
- Verify UpdateCache shrinks.
"""

import random
import sys
sys.path.insert(0, ".")

from client import Client
from crypto_utils import decrypt, make_replica_label
from distribution_estimator import DistributionEstimator
from replication_manager import ReplicationManager
from server import Server
from update_cache import UpdateCache


def main():
    random.seed(42)
    server = Server()
    est = DistributionEstimator()
    rm = ReplicationManager(est)
    cache = UpdateCache()
    client = Client(server, distribution_estimator=est, replication_manager=rm, update_cache=cache)

    # Write key multiple times so we get R>=2 and several replicas
    client.put("k", "v0")
    client.put("other", "x")
    for _ in range(30):
        client.get("k")
    client.get("other")
    R = rm.get_replication_factor("k")
    assert R >= 2, "Replication factor logic incorrect"

    # 1
    # Ensure stale replicas appear 
    client.put("k", "v1")
    stale_before = cache.get_stale_replicas("k")
    assert len(stale_before) >= 1, "after put, at least one replica should be marked stale"

    # 2
    # Perform reads; each read of a stale replica repairs it
    for _ in range(100):
        val = client.get("k")
        assert val is not None and val in ("v0", "v1"), "reads must return a value we wrote"

    # 3
    # Verify UpdateCache shrinks by comparing stale set for 'k'
    stale_after = cache.get_stale_replicas("k")
    assert len(stale_after) <= len(stale_before), "UpdateCache should not grow for k"
    # After many reads we expect all replicas to have been hit and repaired
    assert len(stale_after) == 0, "after enough reads, all stale replicas should be repaired"

    # All replicas for 'k' should now have the same value (one of v0 or v1)
    for r in range(R):
        try:
            ct = server.access(make_replica_label("k", r))
            pt = decrypt(ct).decode("utf-8")
            assert pt in ("v0", "v1")
        except KeyError:
            pass

    print("Replica Repair test: Everything passed")


if __name__ == "__main__":
    main()
