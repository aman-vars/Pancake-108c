"""
Server for the baseline encrypted key-value store.
Wraps storage; exposes access and write.
Server never sees plaintext keys or values—only labels and ciphertexts.
"""

from storage import Storage


class Server:
    """Wraps storage. Exposes access(label) and write(label, ciphertext)."""

    def __init__(self) -> None:
        self._storage = Storage()

    def access(self, label: bytes) -> bytes:
        """Return ciphertext for the given label. Raises KeyError if not found."""
        ciphertext = self._storage.get(label)
        if ciphertext is None:
            raise KeyError("label not found")
        return ciphertext

    def write(self, label: bytes, ciphertext: bytes) -> None:
        """Store ciphertext under the given label."""
        self._storage.put(label, ciphertext)
