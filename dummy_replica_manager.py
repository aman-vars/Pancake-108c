"""
DummyReplicaManager keeps total server entries = 2n by adding/removing dummy replicas.
Uses a dedicated dummy key; dummy replica IDs are managed in insertion order so
add/remove are consistent. When R(k) increases, new replica slots are allocated through
converting a dummy replica to hold (k, j)'s value (replica swapping). This ensures that
the total stays 2n.
"""

import os
from typing import Dict, Tuple
from crypto_utils import make_replica_label

DUMMY_KEY = "*DUMMY*"
CIPHERTEXT_LENGTH = 284 # Match real ciphertext length -> nonce(12) + encrypted_block(256) + tag(16)


class DummyReplicaManager:
    """
    INVARIANT: total replicas must equal 2n.
    Adds or removes dummy replicas to ensure invariant.
    When a key gains replicas (R(k) increases), converts dummy
    slots to real slots via replica swapping.
    """

    def __init__(self, server, replication_manager) -> None:
        self._server = server
        self._rm = replication_manager
        self._dummy_ids = []
        self._swap_mapping = {}

    def rebalance(self) -> None:
        """Adjust dummy count so that server.size() == 2n (add or remove dummies only)."""
        target = self._rm.get_total_replica_target()
        current_size = self._server.size()
        if current_size < target: # Need to add dummies
            self._add_dummies(target - current_size)
        elif current_size > target: # Need to remove dummies
            self._remove_dummies(current_size - target)

    def _add_dummies(self, count) -> None:
        """Append `count` new dummy replicas and insert them."""
        next_id = (max(self._dummy_ids) + 1) if self._dummy_ids else 0
        for i in range(count):
            replica_id = next_id + i
            label = make_replica_label(DUMMY_KEY, replica_id)
            self._server.write(label, os.urandom(CIPHERTEXT_LENGTH))
            self._dummy_ids.append(replica_id)

    def _remove_dummies(self, count: int) -> None:
        """
        Remove `count` dummy replicas from the server. 
        Only removes dummy replicas still in `_dummy_ids`,
        meaning true dummy replicas.
        """
        
        removed = 0
        while removed < count and self._dummy_ids:
            replica_id = self._dummy_ids.pop()
            label = make_replica_label(DUMMY_KEY, replica_id)
            self._server.delete(label)
            removed += 1

    def get_label(self, key, replica_id) -> bytes:
        """Returns the server label for the replica. Can be canonical or swapped."""
        if (key, replica_id) in self._swap_mapping:
            return self._swap_mapping[(key, replica_id)]
        return make_replica_label(key, replica_id)

    def ensure_replica_exists(self, key, replica_id, ciphertext) -> None:
        """
        Ensure the replica (key, replica_id) exists on the server.
        If the canonical label was never written, convert a dummy replica 
        by writing value to dummy label (swapping).
        """
        
        if (key, replica_id) in self._swap_mapping: # Replica already is in dummy slot
            return
        try: # Successful if replica exists
            self._server.access(make_replica_label(key, replica_id))
            return
        except KeyError:
            pass
        if not self._dummy_ids:
            raise RuntimeError("No dummy replica available for swap; invariant 2n may be broken or rebalance needed.")
        
        # Overwrite dummy into replica
        dummy_id = self._dummy_ids.pop()
        label = make_replica_label(DUMMY_KEY, dummy_id)
        self._server.write(label, ciphertext)
        self._swap_mapping[(key, replica_id)] = label 

    def get_dummy_replica_ids(self) -> list[int]:
        """
        Returns the list of dummy replica IDs 
        (only includes slots that still hold dummy content).
        """
        
        return list(self._dummy_ids)
