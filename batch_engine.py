# batch_engine.py
"""
Fixed-size batching layer.
Expands each PUT/GET query into B server accesses. 1 real + (B-1) padding.
Also enforces read-then-write formatting to hide batch operation-type.
"""

import os
import random
from typing import Optional
from crypto_utils import LABEL_LENGTH
from crypto_utils import encrypt


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
        First performs B reads, then B writes. 1 of the writes are real
        and the other (B-1) writes are padding. Padded writes use random labels 
        and random ciphertext. Real write gets the given ciphertext.
        """
        slots = [(label, True)]  
        # Pad, then shuffle
        for _ in range(self._batch_size - 1):
            if self._fake_distribution_manager:
                fake_label = self._fake_distribution_manager.sample_fake_label()
            else:
                fake_label = self._random_label()
            slots.append((fake_label, False))
        random.shuffle(slots)

        # Read to mask operation
        read_results = []
        for lbl, is_real in slots:
            try:
                ct = self._server.access(lbl)
                read_results.append((lbl, ct, is_real))
            except KeyError:
                read_results.append((lbl, None, is_real))

        # Write to server
        for lbl, ct, is_real in read_results:
            if is_real:
                self._server.write(lbl, ciphertext)
            else:
                if ct is None: 
                    ct = encrypt(b"dummy")
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

        # Write to mask operation: reuse ciphertext from the batch so we never introduce new data
        for lbl, ct in read_results:
            if ct is None:  # Fake miss: reuse real slot's ciphertext to preserve storage state
                ct = real_result
            self._server.write(lbl, ct)

        return real_result
