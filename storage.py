"""
In-memory storage for the baseline encrypted key-value store.
Maps opaque label (bytes) -> ciphertext (bytes).
No knowledge of plaintext keys or values.
"""

from typing import Optional


class Storage:
    """Simple in-memory dictionary: label -> ciphertext. All values are opaque bytes."""

    def __init__(self) -> None:
        self._store: dict[bytes, bytes] = {}

    def get(self, label: bytes) -> Optional[bytes]:
        """Return ciphertext for the given label, or None if not found."""
        return self._store.get(label)

    def put(self, label: bytes, ciphertext: bytes) -> None:
        """Store ciphertext under the given label."""
        self._store[label] = ciphertext
