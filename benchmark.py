# benchmark.py
"""
Benchmark for Pancake system.

Measures:
- throughput (requests/sec)
- latency (ms/request)
"""

import time
import random

from client import Client
from crypto_utils import decrypt, make_replica_label, encrypt
from proxy import Proxy
from server import Server
from batch_engine import BatchEngine
from distribution_estimator import DistributionEstimator
from replication_manager import ReplicationManager
from dummy_replica_manager import DummyReplicaManager
from fake_distribution import FakeDistributionManager
from update_cache import UpdateCache


NUM_KEYS = 500
NUM_REQUESTS = 1000
WARMUP = 100
BATCH_SIZE = 3
SKEW = 5



class Baseline:
    """Simple encrypted key value store. No pancake"""
    
    def __init__(self, server) -> None:
        self._server = server
        
    def put(self, key, value):
        label = make_replica_label(key, 0)
        ct = encrypt(value.encode())
        self._server.write(label, ct)
        
    def get(self, key):
        label = make_replica_label(key, 0)
        try: 
            ct = self._server.access(label)
        except KeyError:
            return None
        return decrypt(ct).decode()


def setup_baseline():
    server = Server()
    client = Client(Baseline(server))
    return client



def setup_pancake():
    """Set up full system for pancake."""
    # Server
    server = Server()
    # Proxy helpers
    estimator = DistributionEstimator()
    replication_manager = ReplicationManager(estimator)
    update_cache = UpdateCache()
    dummy_manager = DummyReplicaManager(server, replication_manager)
    fake_distribution = FakeDistributionManager(replication_manager, dummy_replica_manager=dummy_manager)
    batch_engine = BatchEngine(server, fake_distribution_manager=fake_distribution, batch_size=BATCH_SIZE)
    # Proxy
    proxy = Proxy(batch_engine, distribution_estimator=estimator, replication_manager=replication_manager, update_cache=update_cache, dummy_manager=dummy_manager)
    # Client
    client = Client(proxy)
    return client


def generate_hot_key_distribution(keys):
    """
    Generates skewed workload.
    (1-`SKEW`)% of accesses go to `SKEW`% of keys.
    Defines a function that builds a samplign function for keys.
    """
    
    hot_keys = keys[:int(len(keys) * SKEW/100)]

    # generates keys following skewed distribution
    def sample():
        if random.random() < (1-SKEW/100):
            return random.choice(hot_keys)
        return random.choice(keys)

    return sample # returns function 


def benchmark_put(client, keys):
    """Benchmark PUT operations"""
    start = time.time()
    for i in range(NUM_REQUESTS):
        key = random.choice(keys)
        value = f"value_{i}"
        client.put(key, value)
    end = time.time()

    throughput = NUM_REQUESTS / (end-start)
    latency = ((end-start) / NUM_REQUESTS) * 1000
    return throughput, latency


def benchmark_get(client, keys):
    """Benchmark GET operations"""
    sample_key = generate_hot_key_distribution(keys)

    start = time.time()
    for _ in range(NUM_REQUESTS):
        key = sample_key()
        client.get(key)
    end = time.time() 

    throughput = NUM_REQUESTS / (end-start)
    latency = ((end-start) / NUM_REQUESTS) * 1000
    return throughput, latency


def warmup(client, keys):
    """Warmup phase to set up database with values."""
    for i in range(WARMUP):
        client.put(keys[i], f"value_{i}")



def main():
    # 1. ekv 
    print()
    print(" ==== Encrypted Key Value Benchmark ====")
    
    # setup
    print("Setting up...")
    b_client = setup_baseline()
    keys = [f"key_{i}" for i in range(NUM_KEYS)]
    print("Setup complete")
    
    # warmup
    print("Warming up...")
    warmup(b_client, keys)
    print("Warmup complete")
    
    # metrics
    print("Benchmarking PUT...")
    b_put_xput, b_put_lat = benchmark_put(b_client, keys)
    print("Benchmarking GET,..")
    b_get_xput, b_get_lat = benchmark_get(b_client, keys)
    print()
    
    
    # 2. pancake
    print(" ==== Pancake Baseline Benchmark ==== ")

    # setup
    print("Setting up...")
    p_client = setup_pancake()
    print("Setup complete")

    # warmup
    print("Warming up...")
    warmup(p_client, keys)
    print("Warmup complete")

    # metrics
    print("Benchmarking PUT...")
    p_put_xput, p_put_lat = benchmark_put(p_client, keys)
    print("Benchmarking GET...")
    p_get_xput, p_get_lat = benchmark_get(p_client, keys)

    print()
    
    # 3. results
    print("Results for EKV:")
    print(f"    PUT throughput : {b_put_xput} req/s")
    print(f"    PUT latency    : {b_put_lat} ms")
    print()
    print(f"    GET throughput : {b_get_xput} req/s")
    print(f"    GET latency    : {b_get_lat} ms")
    print()
    print("Results for Pancake:")
    print(f"    PUT throughput : {p_put_xput} req/s")
    print(f"    PUT latency    : {p_put_lat} ms")
    print()
    print(f"    GET throughput : {p_get_xput} req/s")
    print(f"    GET latency    : {p_get_lat} ms")
    print()
    
    
    

if __name__ == "__main__":
    main()