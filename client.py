"""
Client (trusted proxy) for the baseline encrypted key-value store.
Performs all cryptographic operations; server only sees labels and ciphertexts.
"""

from typing import Optional
from crypto_utils import decrypt, encrypt, prf
from server import Server


class Client:
    """Client: put(key, value) and get(key). All crypto is done here."""

    def __init__(self, server: Server) -> None:
        self._server = server

    def put(self, key: str, value: str) -> None:
        """Store value under key. Converts key to label, pads and encrypts value."""
        key_bytes = key.encode("utf-8")
        label = prf(key_bytes)
        value_bytes = value.encode("utf-8")
        ciphertext = encrypt(value_bytes)
        self._server.write(label, ciphertext)

    def get(self, key: str) -> Optional[str]:
        """Retrieve value for key. Returns None if key is not stored."""
        key_bytes = key.encode("utf-8")
        label = prf(key_bytes)
        try:
            ciphertext = self._server.access(label)
        except KeyError:
            return None
        plaintext_bytes = decrypt(ciphertext)
        return plaintext_bytes.decode("utf-8")
