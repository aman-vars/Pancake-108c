# tests/batching_v1.py
"""
Tests for fixed-size batching.
- Each logical PUT triggers B server writes.
- Each logical GET triggers B server accesses.
"""

import sys
sys.path.insert(0, ".")
import random
import string
import sys

from batch_engine import BatchEngine
from proxy import Proxy
from server import Server
from client import Client


BATCH_SIZE = 3


class BatchingBenchmarkServer:
    """Wraps a Server and counts write/access calls. Used to verify B calls per request."""

    def __init__(self, server: object) -> None:
        self._server = server
        self.write_count = 0
        self.access_count = 0

    def reset(self) -> None:
        self.write_count = 0
        self.access_count = 0

    def write(self, label: bytes, ciphertext: bytes) -> None:
        self.write_count += 1
        self._server.write(label, ciphertext)

    def access(self, label: bytes) -> bytes:
        self.access_count += 1
        return self._server.access(label)



def random_string(min_len: int = 1, max_len: int = 200) -> str:
    """Generate a random string of printable ASCII."""
    length = random.randint(min_len, max_len)
    return "".join(random.choices(string.ascii_letters + string.digits + " ", k=length))


def test_correctness() -> None:
    """Batched client must behave like baseline."""
    server = Server()
    counted = BatchingBenchmarkServer(server)
    engine = BatchEngine(counted, batch_size=BATCH_SIZE)
    proxy = Proxy(engine)
    client = Client(proxy)

    n = 1000
    keys = [f"key_{i}" for i in range(n)]
    values = [random_string() for _ in range(n)]
    data = dict(zip(keys, values))

    for k, v in data.items():
        client.put(k, v)

    store = server._storage._store
    for label, ciphertext in store.items():
        assert isinstance(label, bytes) and isinstance(ciphertext, bytes)

    read_order = list(data.keys())
    random.shuffle(read_order)
    for k in read_order:
        got = client.get(k)
        assert got is not None, f"Missing key: {k}"
        assert got == data[k], f"Mismatch for {k}: expected {data[k]!r}, got {got!r}"

    assert client.get("key_nonexistent") is None
    print("  correctness: passed (1000 keys insert + random read + nonexistent)")


def test_exactly_b_server_calls() -> None:
    """Each logical put triggers B writes; each logical get triggers B accesses + B writes (read-then-write)."""
    server = Server()
    counted = BatchingBenchmarkServer(server)
    engine = BatchEngine(counted, batch_size=BATCH_SIZE)
    proxy = Proxy(engine)
    client = Client(proxy)

    # 1 put -> B writes, 0 accesses
    counted.reset()
    client.put("k1", "v1")
    assert counted.write_count == BATCH_SIZE, f"expected {BATCH_SIZE} writes, got {counted.write_count}"
    assert counted.access_count == 0

    # 1 get -> B accesses then B writes
    counted.reset()
    _ = client.get("k1")
    assert counted.access_count == BATCH_SIZE, f"expected {BATCH_SIZE} accesses, got {counted.access_count}"
    assert counted.write_count == BATCH_SIZE, f"expected {BATCH_SIZE} writes (read-then-write), got {counted.write_count}"

    # Get dne: B accesses, 0 writes (KeyError before write-back)
    counted.reset()
    result = client.get("nonexistent")
    assert result is None
    assert counted.access_count == BATCH_SIZE
    assert counted.write_count == 0

    print("  instrumentation: each logical request triggers exactly B server calls")


def main() -> None:
    print("Batching tests:")
    test_correctness()
    test_exactly_b_server_calls()
    print("All batching tests passed.")
    sys.exit(0)


if __name__ == "__main__":
    main()
