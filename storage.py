# storage.py
"""
In-memory storage for encrypted key-value store.
Maps opaque label -> ciphertext.
No knowledge of plaintext keys or values.
"""

from typing import Optional


class Storage:
    """Dictionary in-memory storage: label -> ciphertext. All values are opaque bytes."""

    def __init__(self) -> None:
        self._store: dict[bytes, bytes] = {}

    def get(self, label: bytes) -> Optional[bytes]:
        """Return ciphertext for the given label, or None if not found."""
        return self._store.get(label)

    def put(self, label: bytes, ciphertext: bytes) -> None:
        """Store ciphertext under the given label."""
        self._store[label] = ciphertext

    def delete(self, label: bytes) -> None:
        """Remove the label from storage. Nothing happens if label not present."""
        self._store.pop(label, None)

    def size(self) -> int:
        """Return the number of entries (for testing)."""
        return len(self._store)
