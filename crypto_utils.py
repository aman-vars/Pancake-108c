"""
Cryptographic utilities for the baseline encrypted key-value store.
- PRF (HMAC-SHA256) for deriving labels from plaintext keys.
- Authenticated encryption (AES-GCM).
- Fixed-length padding for values to avoid length leakage.
"""

import hashlib
import hmac
import os
import struct
# Fixed plaintext block size before encryption (bytes).
# Values are padded to this size so server cannot infer length.
VALUE_BLOCK_SIZE = 256

# AES-GCM nonce length (96 bits recommended).
NONCE_LENGTH = 12

# HMAC-SHA256 output length (used as label size).
LABEL_LENGTH = 32


def _get_master_key() -> bytes:
    """Return the single master key (32 bytes for AES-256)."""
    # In a real system this would be loaded from secure storage.
    # For this prototype we derive a fixed key from a constant seed.
    return hashlib.sha256(b"pancake-baseline-master-key-v1").digest()


def prf(plaintext_key: bytes) -> bytes:
    """
    Pseudo-random function: plaintext key -> fixed-length label.
    Uses HMAC-SHA256 with the master key.
    Same key always produces the same label; different keys produce different labels.
    """
    key = _get_master_key()
    return hmac.new(key, plaintext_key, hashlib.sha256).digest()


def _pad_value(plaintext: bytes) -> bytes:
    """
    Pad plaintext to VALUE_BLOCK_SIZE for encryption.
    Format: 4-byte length (big-endian) + plaintext + zero padding.
    Decoder can recover original length and strip padding.
    """
    if len(plaintext) > VALUE_BLOCK_SIZE - 4:
        raise ValueError(f"Value too long (max {VALUE_BLOCK_SIZE - 4} bytes)")
    length_bytes = struct.pack(">I", len(plaintext))
    padded = length_bytes + plaintext + b"\x00" * (VALUE_BLOCK_SIZE - 4 - len(plaintext))
    assert len(padded) == VALUE_BLOCK_SIZE
    return padded


def _unpad_value(padded: bytes) -> bytes:
    """Remove padding and return original plaintext."""
    if len(padded) != VALUE_BLOCK_SIZE:
        raise ValueError("Invalid padded block length")
    (length,) = struct.unpack(">I", padded[:4])
    if length > VALUE_BLOCK_SIZE - 4:
        raise ValueError("Invalid length in padded block")
    return padded[4 : 4 + length]


def encrypt(plaintext_bytes: bytes) -> bytes:
    """
    Authenticated encryption: plaintext -> ciphertext.
    Pads to fixed length, then encrypts with AES-256-GCM.
    Ciphertext format: nonce (12 bytes) + ciphertext + tag (16 bytes).
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    padded = _pad_value(plaintext_bytes)
    key = _get_master_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(NONCE_LENGTH)
    ciphertext_with_tag = aesgcm.encrypt(nonce, padded, None)
    return nonce + ciphertext_with_tag


def decrypt(ciphertext_bytes: bytes) -> bytes:
    """
    Authenticated decryption: ciphertext -> plaintext.
    Verifies GCM tag, then decrypts and unpads.
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    if len(ciphertext_bytes) < NONCE_LENGTH + 16:
        raise ValueError("Ciphertext too short")
    nonce = ciphertext_bytes[:NONCE_LENGTH]
    encrypted = ciphertext_bytes[NONCE_LENGTH:]
    key = _get_master_key()
    aesgcm = AESGCM(key)
    padded = aesgcm.decrypt(nonce, encrypted, None)
    return _unpad_value(padded)
