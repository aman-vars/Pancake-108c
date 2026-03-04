import os
from crypto_utils import make_replica_label

DUMMY_KEY = " dummy "


class DummyReplicaManager:
    """Ensures total server entries = 2n by inserting dummy replica entries."""
    
    def __init__(self, server, replication_manager) -> None:
        self._server = server
        self._rm = replication_manager
        self._dummy_ids = set()
        
    def rebalance(self) -> None: 
        """Ensures total replicas = 2n."""
        # Calculate # of dummies needed
        n = len(self._rm._estimator.get_distribution())
        target = 2 * n
        real = self._rm.total_real_replicas()
        dummys_needed = max(0, target - real)
        
        current_dummy = len(self._dummy_ids)
        
        if dummys_needed > current_dummy:
            self._add_dummies(dummys_needed - current_dummy)
        elif dummys_needed < current_dummy:
            self._remove_dummies(current_dummy - dummys_needed)
            
    