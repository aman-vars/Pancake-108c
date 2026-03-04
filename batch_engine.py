# batch_engine.py
"""
Fixed-size batching layer for the encrypted key-value store.
Sits between Proxy and Server: each logical PUT/GET is expanded into
exactly B server accesses (1 real + (B-1) padding).
"""

import os
import random
from typing import Optional

from crypto_utils import LABEL_LENGTH


class BatchEngine:
    """
    Intercepts PUT/GET at the server boundary and expands each into
    exactly B server accesses: 1 real + (B-1) padding.
    Proxy sees the same interface as Server (write, access); only
    the underlying server sees B accesses per logical operation.
    """

    def __init__(self, server: object, batch_size: int = 3) -> None:
        if batch_size < 1:
            raise ValueError("batch_size must be >= 1")
        self._server = server
        self._B = batch_size

    def _random_label(self) -> bytes:
        """Return a random label (not real key)."""
        return os.urandom(LABEL_LENGTH)

    def write(self, label: bytes, ciphertext: bytes) -> None:
        """
        Perform 1 real write plus (B-1) padding writes so the server
        sees exactly B writes. Padded writes uses random labels and random
        ciphertext; only the real write persists meaningful data.
        """
        
        slots: list[tuple[bytes, bytes]] = [(label, ciphertext)]
        # Pad, then shuffle
        for _ in range(self._B - 1):
            slots.append((self._random_label(), os.urandom(len(ciphertext))))
        random.shuffle(slots)
        # Write to server
        for lbl, ct in slots: 
            self._server.write(lbl, ct)

    def access(self, label: bytes) -> bytes:
        """
        Perform 1 real access plus (B-1) padding accesses so the server
        sees exactly B accesses. Padded accesses uses random labels and 
        ignores KeyErrors. Returns only the real result (ignoring the case
        of padding label being real label).
        """
        
        slots = [(label, True)]
        # Pad, then shuffle
        for _ in range(self._B - 1): 
            slots.append((self._random_label(), False))
        random.shuffle(slots) 
        real_result: Optional[bytes] = None
        real_missing = False
        # Search for real label
        for lbl, is_real in slots: 
            try:
                ct = self._server.access(lbl)
                if is_real:
                    real_result = ct
            except KeyError:
                if is_real:
                    real_missing = True # not found
        if real_missing or real_result is None:
            raise KeyError("label not found")
        return real_result
