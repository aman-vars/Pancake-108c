# proxy.py
"""
Trusted proxy that executes client's requests.
Performs all cryptographic operations.
Handles batching, selective replication, and fake distribution in query. 
"""

import random
from typing import Optional, TYPE_CHECKING
from crypto_utils import decrypt, encrypt, make_replica_label
from server import Server

if TYPE_CHECKING: # To prevent circular imports
    from distribution_estimator import DistributionEstimator
    from replication_manager import ReplicationManager
    from update_cache import UpdateCache
    from dummy_replica_manager import DummyReplicaManager


class Proxy:
    """
    Supports `put(key, value)` and `get(key)`. 
    Handles encryption and Pancake properties for security.
    """ 

    def __init__(self, server: Server, distribution_estimator = None, replication_manager = None, update_cache = None, dummy_manager = None) -> None:
        self._server = server
        self._distribution_estimator = distribution_estimator
        self._replication_manager = replication_manager
        self._update_cache = update_cache
        self._dummy_manager = dummy_manager

    def put(self, key: str, value: str) -> None:
        """Store value in server. Writes to 1 replica and marks others stale when using replication."""
        # Increment access total for key
        if self._distribution_estimator:
            self._distribution_estimator.record_access(key)
            
        # Encrypt
        value_bytes = value.encode("utf-8")
        ciphertext = encrypt(value_bytes)

        # Calculate replica id for label
        if self._replication_manager:
            R = self._replication_manager.get_replication_factor(key)
            replica_id = random.randint(0, R-1)
            label = make_replica_label(key, replica_id)
            # Put in server
            self._server.write(label, ciphertext)
            # Mark stale replicas
            if self._update_cache:
                stales = (set(range(R)) - {replica_id}) # Set of stale replicas
                if stales:
                    self._update_cache.mark_stale(key, stales)
                # Clear the updated replica from stale set (in case it was previously marked) 
                self._update_cache.clear_replica(key, replica_id)
                self._update_cache.remove_key_if_empty(key) 
        else:
            label = make_replica_label(key, 0)
            self._server.write(label, ciphertext)
            
        # Add dummy replicas if needed
        if self._dummy_manager:
            self._dummy_manager.rebalance()

    def get(self, key: str) -> Optional[str]:
        """Retrieve value for key, or None. Repairs stale replica if read."""
        # Increment access total for key
        if self._distribution_estimator:
            self._distribution_estimator.record_access(key)
            
        # Calculate replica id for label
        if self._replication_manager: 
            R = self._replication_manager.get_replication_factor(key)
            replica_id = random.randint(0, R-1) 
        else:
            replica_id = 0
        label = make_replica_label(key, replica_id)

        # Search for label
        try:
            ciphertext = self._server.access(label)
        except KeyError:
            return None
        plaintext_bytes = decrypt(ciphertext)

        # If the read replica was stale, repair it
        if self._update_cache:
            stale = self._update_cache.get_stale_replicas(key)
            if replica_id in stale:
                self._server.write(label, encrypt(plaintext_bytes)) # Re-encrypt to preserve security
                self._update_cache.clear_replica(key, replica_id)
                self._update_cache.remove_key_if_empty(key)

        return plaintext_bytes.decode("utf-8")
