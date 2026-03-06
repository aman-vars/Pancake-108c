"""
Generates fake replica accesses to pad batches.

"""

from crypto_utils import make_replica_label
from replication_manager import ReplicationManager
import random

class FakeDistributionManager:
    """Generates fake replica accesses."""
    
    def __init__(self, replication_manager: ReplicationManager = None) -> None:
        self._replication_manager = replication_manager
    
    
    def _all_replicas(self):
        """Returns a list of all (key, replica_id) pairs currently present."""
        replicas = []
        replication_factors = self._replication_manager.get_all_replication_factors()
        for key, R in replication_factors.items():
            for replica_id in range(R):
                replicas.append( (key, replica_id) )
        return replicas
    
    def sample_fake_replicas(self) -> (str, int):
        """Randomly select 1 replica out of all them."""
        replicas = self._all_replicas()
        if not replicas:
            raise RuntimeError("No replicas available for fake sampling")
        return random.choice(replicas)
        
    def sample_fake_label(self) -> bytes:
        """Return the storage label for a sampled fake replica."""
        key, replica_id = self.sample_fake_replicas()
        return make_replica_label(key,replica_id)