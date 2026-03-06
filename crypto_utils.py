# crypto_utils.py
"""
Performs the cryptographic utilities.
- PRF (HMAC-SHA256) for deriving labels from plaintext keys.
- Encryption using AES-GCM.
- Fixed-length padding for values to avoid length leakage.
"""

import hashlib
import hmac
import os
import struct
from cryptography.hazmat.primitives.ciphers.aead import AESGCM # type:ignore
    
# Pad values to 256 bytes before encryption to avoid length leakage
VALUE_BLOCK_SIZE = 256
# AES-GCM nonce length (12 bytes * 8 = 96 bits).
NONCE_LENGTH = 12
# HMAC-SHA256 output label length (32 bytes * 8 = 256 bits).
LABEL_LENGTH = 32


def _get_master_key() -> bytes:
    """Generate and return secret key for PRF and encryption."""
    return hashlib.sha256(b"pancake-extension-master-key-123").digest() # 32 bytes


def prf(plaintext_key: bytes) -> bytes:
    """Deterministically converts a plaintext key into a fixed-size pseudorandom label."""
    key = _get_master_key()
    return hmac.new(key, plaintext_key, hashlib.sha256).digest()


def make_replica_label(key: str, replica_id: int) -> bytes:
    """
    Derives the deterministic storage label for a replica
    Label is generated through a PRF function.
    """
    
    replica_input = f"{key}|{replica_id}".encode("utf-8")
    return prf(replica_input)


def _pad_value(plaintext: bytes) -> bytes:
    """Pad plaintext to allow for secure encryption."""
    # Pack plaintext length into 4 bytes
    plaintext_length = len(plaintext)
    if plaintext_length > VALUE_BLOCK_SIZE-4: # Must be at least 4 available bytes 
        raise ValueError(f"Value too long (max {VALUE_BLOCK_SIZE - 4} bytes)")
    length_bytes = struct.pack(">I", plaintext_length) 
    
    # Pad
    padding_size = VALUE_BLOCK_SIZE - 4 - plaintext_length
    padding_bytes = b"\x00" * padding_size
    padded_block = length_bytes + plaintext + padding_bytes
    return padded_block


def _unpad_value(padded_block: bytes) -> bytes:
    """Remove padding and return original plaintext."""
    # Verify correct size
    if len(padded_block) != VALUE_BLOCK_SIZE: 
        raise ValueError("Invalid padded block size")
    
    # Read stored plaintext length
    length_bytes = padded_block[:4]
    plaintext_length = struct.unpack(">I", length_bytes)[0]
    if plaintext_length > VALUE_BLOCK_SIZE-4:
        raise ValueError("Invalid plaintext length")
    
    # Original plaintext
    return padded_block[4 : plaintext_length+4]


def encrypt(plaintext_bytes: bytes) -> bytes:
    """
    Encrypts plaintext. First pads to fixed length. Then uses AES-GCM.
    Ciphertext format: nonce (12 bytes) + ciphertext + tag (16 bytes).
    """
    
    padded_value = _pad_value(plaintext_bytes)
    key = _get_master_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(NONCE_LENGTH)
    ciphertext_with_tag = aesgcm.encrypt(nonce, padded_value, None)
    return nonce + ciphertext_with_tag


def decrypt(ciphertext_bytes: bytes) -> bytes:
    """Decrypts ciphertext. First verifies GCM tag, then decrypts and unpads."""
    if len(ciphertext_bytes) < NONCE_LENGTH + 16:
        raise ValueError("Ciphertext too short")
    
    nonce = ciphertext_bytes[:NONCE_LENGTH]
    encrypted = ciphertext_bytes[NONCE_LENGTH:]
    key = _get_master_key()
    aesgcm = AESGCM(key)
    padded = aesgcm.decrypt(nonce, encrypted, None)
    return _unpad_value(padded)
