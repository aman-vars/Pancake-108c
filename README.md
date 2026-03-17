# Running

1. Clone the repository and go to the directory.
2. Download the requirements in the `requirements.txt`
3. Run `python benchmark.py` to get the benchmark results.

The `benchmark.py` file has different phases:
1. Setup
    - Initializes all of the features needed for Pancake
2. Warmup
    - A small number of PUTs are sent to the server to build the server storage.
    - (not included in the performance metrics)
3. PUT benchmark
    - System handles a lot of random PUTs on randomly chosen keys
    - Measures **xput** and **latency**.
4. GET benchmark
    - System handles a lot of random GETs using a skewed key distribution 
    - A small percent of the workload is accessed in most of the queries to create the skew.
    - Measures **xput** and **latency**.
5. Results
    - Each stage prints its running status
    - At the end, the script prints the PUT results and GET results.



# Design Process 

This project is a research-oriented reimplementation of the Pancake paper in Python. Instead of using a real distributed client–server system (Redis + Thrift), this version *simulates* the cryptographic securities and access-pattern behavior.

**NOTE** that this doesn't incorporate Pancake's access delay functionality. In my implementation, every batch guarantees 1 real access and B-1 fake accesses. The paper's original implementation has more security because batches can have 0, 1, 2, or even 3 real accesses in the batch. I think this leaks some structural information because the server can learn that one batch means one user query. I didn't have time to implement this part of the system.


## Encrypted Key–Value Store

This project is built on top of an encrypted key–value system with modularities between client and server.

### Architecture   

Client 
- Represents the user/application interacting with the system
- Provides `put(key, value)` and `get(key)`
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
- Provides `access(label)` and `write(label, ciphertext)`

Storage
- Dictionary that maps `label -> ciphertext`
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

### Length Padding
To prevent length leakage:
- Values are padded to a fixed block size (256 bytes)
- Format: `4-byte length || plaintext || zero padding`
- Decryption restores original plaintext safely


## Fixed-Size Batching

The BatchEngine layer expands each request into *B* server accesses.

- For this experiment, I used *B = 3* as it was used in the paper. 
- For systems that prioritize security more, B could be set to be higher.
- For each PUT, Pancake issues 1 real write and B-1 fake writes (random labels and random ciphertext).
- For each GET, Pancake issues 1 real access and B-1 fake accesses (random labels).

The order of these requests are randomized so the server cannot determine which is the real one. Batching ensures that real operations are indistinguishable from fake ones. 

Another security weakness that Pancake protects against is the server being able to decipher the operation type for a batch of queries. `access(label)` and `write(label, ciphertext)` is visible to the server. After integrating read-then-write logic, accesses now also write back to the server, and writes also access from the server. This way the operation type is masked to the server since it sees `access(label)` and then `write(label, ciphertext)` for each batch.


## Selective Replication

Selective replication spreads accesses for frequently accessed key across storage locations. 

### Distribution Estimator
Tracks observed key access frequency.

Example access counts: 
- u1 -> 85
- u2 -> 10
- u3 -> 5

Estimated distribution:
- π(u1) = .85
- π(u2) = .10
- π(u3) = .05

### Replication Factors 
Replication factors are determined with the formula: `R(k) = ceil(π(k)/a)`
where `n` is the number of distinct keys and `a` is `1/n`

Calculated Replication factor:
- R(u1) = ceil(.85/.33) = 3
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
- When a key becomes hotter and its replication factor increases, dummy replicas are convertde into real replicas using *replica swapping* so the total number of server entries remains `2n`. Inserting a new entry would break the invariant and leak information.

Replica swapping:
- A dummy replica is chosen.
- The dummmy replica is overwritten with the ciphertext for the new replica.
- Dummy Replica Manager records the mapping so that the replica corresponds to the dummy label.
- If accessing a replica that has been swapped, the Manager checks the records to return the proper label.


## Fake Query Distribution

Even with replication, the server still learns information from how often replicas are accessed. Hot keys will appear more often, even if their accesses are spread out across many replicas. 

To prevent this leakage, Pancake uses frequency smoothing. The goal is to ensure that each access (even across replicas) appears uniformly to the server. This essentially guarantees that cold replicas, especially dummy keys, will be sampled more for padding in the batch engine. 

### Smoothing Equation

I achieved this by using the Pancake smoothing equation:

`(delta * π(k) / R(k)) + ((1 - delta) * π_f(k, j)) = 1/N`

- `delta` is the probability that the access is real
- `π(k)` is the observed access probability of `k`
- `R(k)` is the replication factor for `k`
- `π_f(k, j)` is the fake access probability of replica `j` of `k`
- `N` is the number of total replicas
- For dummy keys, `π(k) = 0` because they aren't ever accessed.

### FakeDistributionManager

- Computes the weights for each replica using the equation.
- Padding accesses are sampled from this weighted distribution now. Before, they were sampled randomly.
- Upholds the security guarantee that the server observes a completely uniform access frequency distribution.



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
- `tests/fake_distribution_smoothing_test.py` - checks that the replica weights generated for fake distribution sampling makes sense.
- `tests/fake_distribution_test.py` - checks that the replicas picked make sense.
- `tests/read_then_write_test.py` - verifies that server can't determine operation type when we use read-then-write logic.