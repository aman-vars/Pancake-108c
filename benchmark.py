"""
Benchmark for Pancake system.

Measures:
- throughput (requests/sec)
- latency (ms/request)
"""

import time
import random

from client import Client
from proxy import Proxy
from server import Server
from batch_engine import BatchEngine
from distribution_estimator import DistributionEstimator
from replication_manager import ReplicationManager
from dummy_replica_manager import DummyReplicaManager
from fake_distribution import FakeDistributionManager
from update_cache import UpdateCache


NUM_KEYS = 100 # 10k
NUM_REQUESTS = 200 # 20k
WARMUP = 20 # 2k
BATCH_SIZE = 3
SKEW = 5


def setup_system():
    """Set up full system."""
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
    print()
    print("Pancake Baseline Benchmark")
    print()

    # setup
    print("Setting up...")
    client = setup_system()
    keys = [f"key_{i}" for i in range(NUM_KEYS)]
    print("Setup complete")

    # warmup
    print("Warming up...")
    warmup(client, keys)
    print("Warmup complete")
    
    print()

    # metrics
    print("Benchmarking PUT...")
    put_xput, put_latency = benchmark_put(client, keys)

    print("Benchmarking GET...")
    get_xput, get_latency = benchmark_get(client, keys)

    print()
    
    # results
    print("Results:")
    print(f"    PUT throughput : {put_xput} req/s")
    print(f"    PUT latency    : {put_latency} ms")

    print()

    print(f"    GET throughput : {get_xput} req/s")
    print(f"    GET latency    : {get_latency} ms")

    print()
    
    
    

if __name__ == "__main__":
    main()