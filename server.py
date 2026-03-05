# server.py
"""
Server for the encrypted key-value store.
Wraps storage (so exposes access and write).
Server never sees plaintext keys or values, only labels and ciphertexts.
"""

from storage import Storage


class Server:
    """Wraps storage class with basic functions."""

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

    def delete(self, label: bytes) -> None:
        """Remove the label from storage. Ignore if not found."""
        self._storage.delete(label)

    def size(self) -> int:
        """Returns total number of stored entries."""
        return self._storage.size()
