#tests/batching_v2.py
"""
Benchmark comparing baseline encrypted KV vs batched encrypted KV.
Reports requests/second (rps) and latency/request for PUT + GET.
"""

import sys
sys.path.insert(0, ".")
import time
from server import Server
from proxy import Proxy
from batch_engine import BatchEngine

BATCH_SIZE = 3
NUM_OPS = 10_000
WARMUP = 1_000


def run_benchmark(name: str, proxy: Proxy, num_ops: int) -> tuple[float, float, float, float]:
    """
    Run PUT then GET workload.
    Return (put_rps, put_latency_ms, get_rps, get_latency_ms).
    """
    
    # KV warmup
    keys = [f"key_{i}" for i in range(num_ops)]
    values = [f"value_{i}" for i in range(num_ops)]

    for i in range(min(WARMUP, num_ops)):
        proxy.put(keys[i], values[i])
    for i in range(min(WARMUP, num_ops)):
        _ = proxy.get(keys[i])

    # Measure PUTs
    start = time.perf_counter()
    for i in range(num_ops):
        proxy.put(keys[i], values[i])
    put_elapsed = time.perf_counter() - start
    put_rps = num_ops / put_elapsed
    put_latency_ms = (put_elapsed / num_ops) * 1000

    # Measure GETs
    start = time.perf_counter()
    for i in range(num_ops):
        _ = proxy.get(keys[i])
    get_elapsed = time.perf_counter() - start
    get_rps = num_ops / get_elapsed
    get_latency_ms = (get_elapsed / num_ops) * 1000

    return put_rps, put_latency_ms, get_rps, get_latency_ms


def main() -> None:
    print("Benchmark: baseline vs batched encrypted KV")
    print(f"Operations per phase: {NUM_OPS}, warmup: {WARMUP}")
    print()

    # Baseline: Proxy -> Server
    server_baseline = Server()
    proxy_baseline = Proxy(server_baseline)
    put_rps_b, put_lat_b, get_rps_b, get_lat_b = run_benchmark("baseline", proxy_baseline, NUM_OPS)

    # Batched: Proxy -> BatchEngine -> Server
    server_batched = Server()
    engine = BatchEngine(server_batched, batch_size=BATCH_SIZE)
    proxy_batched = Proxy(engine)
    put_rps_e, put_lat_e, get_rps_e, get_lat_e = run_benchmark("batched", proxy_batched, NUM_OPS)

    # Print comparisons
    print("Results:")
    print("  Baseline:")
    print(f"    Put:  {put_rps_b:,.0f} req/s,  {put_lat_b:.4f} ms/req")
    print(f"    Get:  {get_rps_b:,.0f} req/s,  {get_lat_b:.4f} ms/req")
    print(f"  Batched (B={BATCH_SIZE}):")
    print(f"    Put:  {put_rps_e:,.0f} req/s,  {put_lat_e:.4f} ms/req")
    print(f"    Get:  {get_rps_e:,.0f} req/s,  {get_lat_e:.4f} ms/req")
    print()
    print("  Comparison (batched / baseline):")
    print(f"    Put RPS ratio:   {put_rps_e / put_rps_b:.3f}  (expected ~1/{BATCH_SIZE})")
    print(f"    Put latency:    {put_lat_e / put_lat_b:.3f}x  (expected ~{BATCH_SIZE}x)")
    print(f"    Get RPS ratio:   {get_rps_e / get_rps_b:.3f}  (expected ~1/{BATCH_SIZE})")
    print(f"    Get latency:    {get_lat_e / get_lat_b:.3f}x  (expected ~{BATCH_SIZE}x)")


if __name__ == "__main__":
    main()
