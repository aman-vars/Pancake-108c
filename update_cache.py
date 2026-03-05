# update_cache.py
"""
Tracks which replica ids are stale for a key.
Mapped via key -> set of stale replica ids.
"""

from typing import Dict, Iterable, Set


class UpdateCache:
    """
    Tracks key -> set of replica ids that are stale.
    """

    def __init__(self) -> None:
        self._cache: Dict[str, Set[int]] = {}

    def mark_stale(self, key: str, replica_ids: Iterable[int]) -> None:
        """Mark the given list of replica ids as stale for key."""
        if key not in self._cache:
            self._cache[key] = set()
        self._cache[key].update(replica_ids)

    def get_stale_replicas(self, key: str) -> Set[int]:
        """Return the set of stale replica ids for key. Empty set if key not tracked."""
        return set(self._cache.get(key, ()))

    def clear_replica(self, key: str, replica_id: int) -> None:
        """Remove the replica id from the stale set for key."""
        if key in self._cache:
            self._cache[key].discard(replica_id) # Ignores KeyError automatically (idempotent)

    def remove_key_if_empty(self, key: str) -> None:
        """If key exists and has no stale replicas, remove the entry."""
        if key in self._cache and len(self._cache[key]) == 0:
            del self._cache[key]
