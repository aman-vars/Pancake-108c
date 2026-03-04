# client.py
"""
Client (trusted proxy) for the baseline encrypted key-value store.
Performs all cryptographic operations; server only sees labels and ciphertexts.
"""

import random
from typing import Optional, TYPE_CHECKING
from crypto_utils import decrypt, encrypt, make_replica_label
from server import Server

if TYPE_CHECKING: # To prevent circular imports
    from distribution_estimator import DistributionEstimator
    from replication_manager import ReplicationManager
    from update_cache import UpdateCache


class Client:
    """Client: put(key, value) and get(key). All crypto is done here."""

    def __init__(self, server: Server, distribution_estimator = None, replication_manager = None, update_cache = None) -> None:
        self._server = server
        self._distribution_estimator = distribution_estimator
        self._replication_manager = replication_manager
        self._update_cache = update_cache

    def put(self, key: str, value: str) -> None:
        """Store value under key. Writes to one replica and marks others stale when using replication."""
        # Increment access total for key
        if self._distribution_estimator is not None:
            self._distribution_estimator.record_access(key)
            
        value_bytes = value.encode("utf-8")
        ciphertext = encrypt(value_bytes)

        # Calculate replica id for label
        if self._replication_manager is not None:
            R = self._replication_manager.get_replication_factor(key)
            replica_id = random.randint(0, R-1) # id = 0 if R == 1, otherwise id = random within range
            label = make_replica_label(key, replica_id)
            self._server.write(label, ciphertext)
            # Mark stale replicas
            if self._update_cache is not None:
                stales = (set(range(R)) - {replica_id}) # Set of stale replicas
                if stales:
                    self._update_cache.mark_stale(key, stales)
                # Clear the updated replica from stale set (in case it was prev marked) 
                self._update_cache.clear_replica(key, replica_id)
                self._update_cache.remove_key_if_empty(key) 
        else:
            label = make_replica_label(key, 0)
            self._server.write(label, ciphertext)

    def get(self, key: str) -> Optional[str]:
        """Retrieve value for key. Returns None if key is not stored."""
        # Increment access total for key
        if self._distribution_estimator is not None: 
            self._distribution_estimator.record_access(key)
            
        # Calculate replica id for label
        if self._replication_manager is not None: 
            R = self._replication_manager.get_replication_factor(key)
            replica_id = random.randint(0, R-1) # id = 0 if R == 1, otherwise id = random within range
        else:
            replica_id = 0
        label = make_replica_label(key, replica_id)
        
        try:
            ciphertext = self._server.access(label)
        except KeyError:
            return None
        
        plaintext_bytes = decrypt(ciphertext)
        return plaintext_bytes.decode("utf-8")
