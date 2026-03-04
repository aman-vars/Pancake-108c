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


class Client:
    """Client: put(key, value) and get(key). All crypto is done here."""

    def __init__(self, server: Server, distribution_estimator: Optional["DistributionEstimator"] = None, replication_manager: Optional["ReplicationManager"] = None) -> None:
        self._server = server
        self._distribution_estimator = distribution_estimator
        self._replication_manager = replication_manager

    def put(self, key: str, value: str) -> None:
        """Store value under key. Converts key to label, pads and encrypts value."""
        if self._distribution_estimator is not None: # Increment total for key
            self._distribution_estimator.record_access(key)
        label = make_replica_label(key, 0)
        value_bytes = value.encode("utf-8")
        ciphertext = encrypt(value_bytes)
        self._server.write(label, ciphertext)

    def get(self, key: str) -> Optional[str]:
        """Retrieve value for key. Returns None if key is not stored."""
        if self._distribution_estimator is not None: # Increment total for key
            self._distribution_estimator.record_access(key)
            
        if self._replication_manager is not None: # calculate replica id for label
            R = self._replication_manager.get_replication_factor(key)
            replica_id = 0 if R <= 1 else random.randint(0, R-1) 
        else:
            replica_id = 0
        label = make_replica_label(key, replica_id)
        
        try:
            ciphertext = self._server.access(label)
        except KeyError:
            return None
        
        plaintext_bytes = decrypt(ciphertext)
        return plaintext_bytes.decode("utf-8")
