# Pancake-Extension Design Process 

This project is a research-oriented reimplementation of the Pancake paper in Python. Instead of using a real distributed client–server system (Redis + Thrift), this version simulates the cryptographic securities and access-pattern behavior.

Goal Checklist:
- Build a minimal encrypted key-value database (done)
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
- No access to plaintext keys or values
- Exposes `access(label)` and `write(label, ciphertext)`

Storage
- In-memory dictionary mapping `label -> ciphertext`
- Treats all data as opaque bytes

Note that there is no networking layer since this is meant to *mimic* client-server.

## Cryptographic Design

### Labels
- Derived using HMAC-SHA256 (PRF)
- Deterministic: same plaintext key to same label
- Pseudorandom: server cannot recover plaintext key
- Fixed length (32 bytes)
- *opaque* so that the server can store and compare them but cannot learn them.

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

Server does not learn:
- Plaintext keys
- Plaintext values
- Value lengths
- Encryption keys

---

## Fixed-size batching

The **BatchEngine** layer sits between Client and Server so each logical request becomes exactly **B** server accesses (1 real + B−1 padding) (B=3 because it was used in Pancake, but it can be modified).

- For each logical PUT, it issues B writes (1 real + random-label/random-ciphertext padding).
- For each logical GET, it issues B accesses (1 real + random-label padding; KeyError on padding is ignored). Access order is randomized.

---

## Testing

- `tests/encrypted_kv_v1.py` — PRF determinism, encryption, 1000-key insert/read.
- `tests/batching_v1.py` — verifies exactly B server calls per request. 
- `tests/benchmark_batching.py` - compares performance between baselines and batched version.
