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

        # Choose replica randomly 
        if self._replication_manager:
            if self._dummy_manager: # Ensure 2n
                self._dummy_manager.rebalance()
            R = self._replication_manager.get_replication_factor(key)
            replica_id = 0 if R == 0 else random.randint(0, R-1) # R == 0 if new key
            if self._dummy_manager:
                if replica_id > 0: # Ensure replica exists
                    self._dummy_manager.ensure_replica_exists(key, replica_id, ciphertext)
                label = self._dummy_manager.get_label(key, replica_id)
            else:
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

        if self._dummy_manager: # Ensure 2n
            self._dummy_manager.rebalance()


    def get(self, key: str) -> Optional[str]:
        """Retrieve value for key, or None. Repairs stale replica if read."""
        # Increment access total for key
        if self._distribution_estimator:
            self._distribution_estimator.record_access(key)
            
        # Choose replica randomly
        if self._replication_manager:
            R = self._replication_manager.get_replication_factor(key)
            replica_id = 0 if R == 0 else random.randint(0, R-1) # if R == 0 -> key shouldn't exist 
            if self._dummy_manager: # Get correct label
                label = self._dummy_manager.get_label(key, replica_id) 
            else:
                label = make_replica_label(key, replica_id)
        else:
            replica_id = 0
            label = make_replica_label(key, 0)

        # Try to read ciphertext
        try:
            ciphertext = self._server.access(label)
        except KeyError:
            # Try to recover by iterating through other dummy replicas of the same key
            # Recovery only possible if key has multiple replicas
            if self._replication_manager and self._dummy_manager and R > 1:
                swapped = False # True if replica id recovered
                for j in range(R):
                    if j == replica_id: # Skip original replica id that was not found
                        continue
                    try: 
                        # If successful, then another replica exists 
                        # read the ciphertext of the other dummy replica and write missing replica by replica swapping
                        other_label = self._dummy_manager.get_label(key, j)
                        ct = self._server.access(other_label)
                        self._dummy_manager.ensure_replica_exists(key, replica_id, ct)
                        label = self._dummy_manager.get_label(key, replica_id)
                        ciphertext = self._server.access(label) # Exists now
                        swapped = True
                        break
                    except KeyError: 
                        continue
                if not swapped: # Recovery failed -> None
                    return None
            else:
                return None

        # Decrypt
        plaintext_bytes = decrypt(ciphertext)

        # If the read replica was stale, repair it
        if self._update_cache:
            stale = self._update_cache.get_stale_replicas(key)
            if replica_id in stale:
                self._server.write(label, encrypt(plaintext_bytes)) # Re-encrypt to preserve security
                self._update_cache.clear_replica(key, replica_id)
                self._update_cache.remove_key_if_empty(key)

        return plaintext_bytes.decode("utf-8")
