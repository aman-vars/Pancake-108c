"""
DummyReplicaManager keeps total server entries = 2n by adding/removing dummy replicas.
Uses a dedicated dummy key; dummy replica IDs are managed in insertion order so
add/remove are consistent.
"""

import os
from crypto_utils import make_replica_label

DUMMY_KEY = "*DUMMY*"
# Match real ciphertext length: nonce(12) + encrypted_block(256) + tag(16)
CIPHERTEXT_LENGTH = 284


class DummyReplicaManager:
    """Ensures total server entries = 2n. Adds or removes dummy replicas as needed."""

    def __init__(self, server, replication_manager) -> None:
        self._server = server
        self._rm = replication_manager
        self._dummy_ids = [] 

    def rebalance(self) -> None:
        """Adjust dummy count so that server.size() == 2n (add or remove dummies only)."""
        target = self._rm.get_total_replica_target()
        current_size = self._server.size()
        if current_size < target: # Need to add dummies
            self._add_dummies(target - current_size)
        elif current_size > target: # Need to remove dummies
            to_remove = current_size - target
            self._remove_dummies(min(to_remove, len(self._dummy_ids)))

    def _add_dummies(self, count: int) -> None:
        """Append `count` new dummy replicas and insert them."""
        next_id = (max(self._dummy_ids) + 1) if self._dummy_ids else 0
        for i in range(count):
            rid = next_id + i
            label = make_replica_label(DUMMY_KEY, rid)
            self._server.write(label, os.urandom(CIPHERTEXT_LENGTH))
            self._dummy_ids.append(rid)

    def _remove_dummies(self, count: int) -> None:
        """Remove count dummy replicas from server."""
        for _ in range(count):
            if not self._dummy_ids:
                break
            rid = self._dummy_ids.pop()
            label = make_replica_label(DUMMY_KEY, rid)
            self._server.delete(label)
