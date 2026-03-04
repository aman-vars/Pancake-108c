import os
from crypto_utils import make_replica_label

DUMMY_KEY = "*DUMMY*"


class DummyReplicaManager:
    """Ensures total server entries = 2n by inserting dummy replica entries."""
    
    def __init__(self, server, replication_manager) -> None:
        self._server = server
        self._rm = replication_manager
        self._dummy_ids = set()
        
    def rebalance(self) -> None: 
        """Ensures total replicas = 2n."""
        # Calculate # of dummies needed
        dummys_needed = self._rm.get_dummy_replica_count()
        
        current_dummy = len(self._dummy_ids)
        
        if dummys_needed > current_dummy:
            self._add_dummies(dummys_needed - current_dummy)
        elif dummys_needed < current_dummy:
            self._remove_dummies(current_dummy - dummys_needed)
            
    def _add_dummies(self, count) -> None:
        """Creates a dummy replica"""
        start = len(self._dummy_ids)

        for i in range(start, start + count):
            label = make_replica_label(DUMMY_KEY, i)
            ciphertext = os.urandom(256)
            self._server.write(label, ciphertext)
            self._dummy_ids.add(i)
            
    def _remove_dummies(self, count) -> None:
        """Removes a dummy replica."""
        for _ in range(count):
            rid = self._dummy_ids.pop()
            label = make_replica_label(DUMMY_KEY, rid)

            try:
                del self._server._storage._store[label]
            except KeyError:
                pass