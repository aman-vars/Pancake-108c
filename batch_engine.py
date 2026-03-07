# batch_engine.py
"""
Fixed-size batching layer.
Expands each PUT/GET query into B server accesses.
1 real + (B-1) padding.
"""

import os
import random
from typing import Optional
from crypto_utils import LABEL_LENGTH
from dummy_replica_manager import CIPHERTEXT_LENGTH


class BatchEngine:
    """
    Expands each PUT/GET into B server accesses, with B usually being 3.
    1 real + (B-1) padding.
    """

    def __init__(self, server, fake_distribution_manager = None, batch_size=3) -> None:
        if batch_size < 1:
            raise ValueError("batch_size must be >= 1")
        self._server = server
        self._batch_size = batch_size
        self._fake_distribution_manager = fake_distribution_manager

    def _random_label(self) -> bytes:
        """Return a random label (not real key)."""
        return os.urandom(LABEL_LENGTH)

    def write(self, label: bytes, ciphertext: bytes) -> None:
        """
        Performs 1 real write and (B-1) padding writes so the server sees B writes. 
        Padded writes uses random labels and random ciphertext.
        Only the real write persists meaningful data.
        """
        
        slots = [(label, ciphertext)]
        # Pad, then shuffle
        for _ in range(self._batch_size - 1):
            slots.append((self._random_label(), os.urandom(len(ciphertext))))
        random.shuffle(slots)
        # Write to server
        for lbl, ct in slots: 
            self._server.write(lbl, ct)

    def access(self, label: bytes) -> bytes:
        """
        Perform 1 real access and (B-1) padding accesses so the server sees B accesses.
        Padding labels are from real replica labels if using FakeDistributionManager.
        Otherwise, random labels are generated.
        """
        
        slots = [(label, True)] # First label is real
        
        # Pad, then shuffle
        for _ in range(self._batch_size - 1): 
            if self._fake_distribution_manager: # Pad using real replicas
                fake_label = self._fake_distribution_manager.sample_fake_label()
            else:
                fake_label = self._random_label()
            slots.append( (fake_label, False) )
        random.shuffle(slots) 
        
        read_results = [] # Stores ciphertexts to write back
        
        # Search for real label
        real_result = None # Will store ciphertext of label to be accessed
        is_real_missing = False
        for lbl, is_real in slots: 
            try:
                ciphertext = self._server.access(lbl)
                if is_real:
                    real_result = ciphertext
                read_results.append((lbl, ciphertext))
            except KeyError:
                if is_real:
                    is_real_missing = True # Not found
                read_results.append((lbl, None))
        if is_real_missing or real_result is None:
            raise KeyError("Label not found.")
        
        # Write to mask operation
        for lbl, ct in read_results:
            if ct is None: # Fake label miss -> random ciphertext
                ct = os.urandom(CIPHERTEXT_LENGTH)
            self._server.write(lbl, ct)
                
        return real_result
