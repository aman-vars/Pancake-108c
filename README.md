# Pancake-Extension

This project is a research-oriented reimplementation of the Pancake paper in Python. Instead of using a real distributed client–server system (e.g., Redis + Thrift), this version simulates the cryptographic securities and access-pattern behavior..

The goal is to:
- Build a minimal encrypted key-value database
- Rebuild Pancake incrementally 
- Benchmark my Pancake implementation
- Integrate an SDa blackbox extension
- Analyze performance results
- Compare the performance differences and create a report

---

## Minimal Encrypted Key–Value Store

This project is built on top of an encrypted key–value system with modularities between client and server.

### Architecture

Client (trusted proxy)
- Performs all cryptographic operations
- Converts plaintext keys into opaque labels using a PRF (HMAC-SHA256)
- Encrypts padded values using AES-256-GCM
- Exposes `put(key, value)` and `get(key)`

Server (untrusted storage layer)
- Stores only opaque labels and ciphertexts
- Has no access to plaintext keys or values
- Exposes `access(label)` and `write(label, ciphertext)`

Storage
- In-memory dictionary mapping `label -> ciphertext`
- Treats all data as opaque bytes

Note that there is no networking layer since this is meant to *mimic* client-server.

---

## Cryptographic Design

### Labels (Searchable Index)
- Derived using HMAC-SHA256 (PRF)
- Deterministic: same plaintext key → same label
- Pseudorandom: server cannot recover plaintext key
- Fixed length (32 bytes)

These labels are *opaque*: the server can store and compare them but cannot interpret or reverse them.

### Value Encryption
- AES-256-GCM (authenticated encryption)
- Random 96-bit nonce per encryption
- Ciphertext format: `nonce || ciphertext || tag`

### Fixed-Length Padding
To prevent length leakage:
- Values are padded to a fixed block size (256 bytes)
- Format: `4-byte length || plaintext || zero padding`
- Decryption restores original plaintext safely

---

## Security Properties 

Server learns:
- Access pattern (same label reused)
- Frequency of accesses
- Timing of operations

Server does NOT learn:
- Plaintext keys
- Plaintext values
- Value lengths
- Encryption keys

---

## Testing

A baseline test script (`test_baseline.py`) verifies:
- PRF determinism
- Encryption/decryption correctness
- Client-server round-trip correctness
- Insertion and retrieval of 1000 keys
