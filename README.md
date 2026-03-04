# Pancake-Extension Design Process 

This project is a research-oriented reimplementation of the Pancake paper in Python. Instead of using a real distributed client–server system (Redis + Thrift), this version *simulates* the cryptographic securities and access-pattern behavior.

Goal Checklist:
- Build a minimal encrypted key-value database (done)
- Rebuild Pancake incrementally 
- Benchmark my Pancake implementation
- Integrate an SDa blackbox extension
- Analyze performance results
- Compare the performance differences and create a report


## Encrypted Key–Value Store

This project is built on top of an encrypted key–value system with modularities between client and server.

### Architecture   

Client 
- Represents the user/application interacting with the system
- Exposes `put(key, value)` and `get(key)`
- Forwards queries to the trusted proxy

Proxy (trusted)
- Performs all of the cryptographic operations
- Converts plaintext keys into opaque labels using a PRF (HMAC_SHA256)
- Encrypts padded values using AES-256-GCM
- Handles batching, selective replication, update tracking, dummy replicas, etc.
- Communicates with the untrusted server to execute query

Server (untrusted storage layer)
- Stores only opaque labels and ciphertexts
- No access to plaintext keys or values
- Exposes `access(label)` and `write(label, ciphertext)`

Storage
- In-memory dictionary mapping `label -> ciphertext`
- Treats all data as opaque bytes

Note that there is no networking layer. Instead, the trusted proxy calls server methods to *mimic* true client-server functionality.


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

### Security Properties 

Server learns:
- Access pattern (same label reused)
- Frequency of accesses
- Timing of operations

Server does not learn:
- Plaintext keys
- Plaintext values
- Value lengths
- Encryption keys


## Fixed-Size Batching

The **BatchEngine** layer sits between Client and Server so each logical request becomes exactly **B** server accesses (1 real + B−1 padding) (B=3 because it was used in Pancake, but it can be modified).

- For each logical PUT, it issues B writes (1 real + random-label/random-ciphertext padding).
- For each logical GET, it issues B accesses (1 real + random-label padding; KeyError on padding is ignored). Access order is randomized.


## Selective Replication

Selective replication spreads accesses for frequently accessed key across storage locations. 

### Distribution Estimator
Tracks observed key access frequency.

Example access counts: 
- u1 -> 85
- u2 -> 10
- u3 -> 5

Estimated distribution:
- π(u1) = .80
- π(u2) = .10
- π(u3) = .05

### Replication Factors 
Replication factors are determined with the formula: `R(k) = ceil(π(k)/a)`
where `n` is the number of distinct keys and `a` is `1/n`

Calculated Replication factor:
- R(u1) = ceil(.80/.33) = 3
- R(u2) = ceil(.10/.33) = 1
- R(u3) = ceil(.05/.33) = 1

### Replica Labels
Each replica appears independent to the server. 

- For GETs, one of the `R(k)` replicas are selected and returned at random.
- For PUTs, only one random replica `r` is updated per write. The rest are marked as stale.


### Update Cache
Tracks which replicas are stale.

- Maps the key -> replica ids
- When a stale replica is accessed during a GET, the proxy repairs it by rewriting the correct ciphertext.

### Dummy Replica Manager
Ensures the invariant of Pancake: the number of total replicas must be `2n` at all times. This prevents the server from learning how many real replicas exist.

- If the number of real replicas is less than  `2n`, the proxy inserts dummy replicas using a dedicated dummy key.
- These dummy keys store random ciphertext indistinguishable from real values 


# Testing

- `tests/encrypted_kv_v1.py` — checks determinism and cryptographic design of labels and data communication.
- `tests/batching_v1.py` — verifies exactly B server calls per request. 
- `tests/benchmark_batching.py` - compares performance between baselines and batched version.
- `tests/distribution_estimator_v1.py` - verifies hotter keys tend to have higher replication factors.
- `tests/replication_test.py` - tests that dummy replica allocation logic in ReplicaManager is secure before actually adding dummies.
- `tests/replica_labels_test.py` - tests the replica label generation function for functionality, specifically determinism.
- `tests/get_replica_selection_test.py` - checks that replica selection on GETs is consistent.
- `tests/put_updatecache_test.py` - ensures that PUTs on existing values (updating) works. Relies on Update Cache
- `tests/replica_repair_test.py` - verifies that stale replicas are repaired on GET queries and removed from Update Cache.
- `tests/dummy_replica_creation_test.py` - ensures invariant that server always stores `2n` replicas.


