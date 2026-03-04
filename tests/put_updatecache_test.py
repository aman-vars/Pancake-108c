"""
Tests for PUT and UpdateCache.
- PUT updates exactly one replica.
- UpdateCache contains the correct stale replicas.
- Multiple PUTs update different replicas over time.
- System still returns correct values for existing replicas.
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


def replica_has_data(server: Server, key: str, replica_id: int) -> bool:
    """True if the server has data for key at replica_id."""
    try:
        server.access(make_replica_label(key, replica_id))
        return True
    except KeyError:
        return False


def replica_with_value(server: Server, key: str, R: int, value: str):
    """Return the replica id that has the given decrypted value for key, or None."""
    for r in range(R):
        try:
            ct = server.access(make_replica_label(key, r))
            pt = decrypt(ct).decode("utf-8")
            if pt == value:
                return r
        except KeyError:
            continue
    return None


def main() -> None:
    random.seed(1)
    server = Server()
    estimator = DistributionEstimator()
    replication_manager = ReplicationManager(estimator)
    update_cache = UpdateCache()
    client = Client(
        server,
        distribution_estimator=estimator,
        replication_manager=replication_manager,
        update_cache=update_cache,
    )

    # Setup
    client.put("hot", "hot_value")
    client.put("cold", "cold_value")
    for _ in range(20):
        client.get("hot")
    client.get("cold")

    R_hot = replication_manager.get_replication_factor("hot")
    R_cold = replication_manager.get_replication_factor("cold")
    assert R_hot >= 2
    assert R_cold == 1

    # 1
    # PUT updates 1 replica
    count_hot = sum(1 for r in range(R_hot) if replica_has_data(server, "hot", r))
    assert count_hot == 1, "each PUT writes to one replica; after one put to hot, exactly one replica has data"

    # Do another PUT so UpdateCache gets stale replicas
    client.put("hot", "v1")

    # 2
    # Verify UpdateCache contains the correct stale replicas 
    # One replica written, the rest marked stale
    stale = update_cache.get_stale_replicas("hot")
    assert len(stale) == R_hot - 1, "stale set must have size R-1"
    assert stale.issubset(set(range(R_hot))), "stale replicas must be in [0, R-1]"
    written = replica_with_value(server, "hot", R_hot, "v1")
    assert written is not None, "v1 was just written to one replica"
    assert written not in stale, "written replica must not be in stale set"

    # 3
    # Multiple PUTs update different replicas over time
    written_ids = set()
    for _ in range(150):
        client.put("hot", "v2")
        w = replica_with_value(server, "hot", R_hot, "v2")
        assert w is not None
        written_ids.add(w)
    assert len(written_ids) >= 2, "over many PUTs we should see different replicas written"

    # 4
    # System still returns correct values 
    # GET may hit any replica but retval must be the one we stored
    client.put("hot", "final_hot")
    client.put("cold", "final_cold")
    for _ in range(30):
        val = client.get("hot")
        if val is not None:
            assert val in ("final_hot", "v2"), "returned value must be one we put"
    for _ in range(10):
        assert client.get("cold") == "final_cold"

    # 5
    # UpdateCache helpers
    # clear_replica and remove_key_if_empty
    stale_set = update_cache.get_stale_replicas("hot")
    for r in list(stale_set):
        update_cache.clear_replica("hot", r)
    update_cache.remove_key_if_empty("hot")
    assert len(update_cache.get_stale_replicas("hot")) == 0

    print("PUT + UpdateCache: all checks passed.")


if __name__ == "__main__":
    main()
