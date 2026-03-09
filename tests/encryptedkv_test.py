# tests/encrypted_kv_v1.py
"""
Test for the encrypted key-value store.
- Verifies PRF: same key -> same label; different keys -> different labels.
- Verifies server storage contains only opaque labels and ciphertexts.
- Inserts 1000 keys (key_0 .. key_999) with random string values.
- Randomly reads keys and asserts returned values match originals.
- Prints confirmation if all tests pass.
"""

import sys
sys.path.insert(0, ".")
import random
import string
import sys

from proxy import Proxy
from batch_engine import BatchEngine
from crypto_utils import prf
from server import Server
from client import Client


def random_string(min_len: int = 1, max_len: int = 200) -> str:
    """Generate a random string of printable ASCII."""
    length = random.randint(min_len, max_len)
    return "".join(random.choices(string.ascii_letters + string.digits + " ", k=length))


def main() -> None:
    # 1
    # Same plaintext key -> same label; different keys -> different labels
    a, b = b"key_a", b"key_b"
    assert prf(a) == prf(a)
    assert prf(b) == prf(b)
    assert prf(a) != prf(b)

    server = Server()
    engine = BatchEngine(server)
    proxy = Proxy(engine)
    client = Client(proxy)

    n = 1000
    keys = [f"key_{i}" for i in range(n)]
    values = [random_string() for _ in range(n)]
    data = dict(zip(keys, values))

    # Insert all
    for k, v in data.items():
        client.put(k, v)

    # 2
    # Server storage: only opaque labels and ciphertexts (bytes only; no plaintext)
    store = server._storage._store
    for label, ciphertext in store.items():
        assert isinstance(label, bytes) and isinstance(ciphertext, bytes)

    # Shuffle and randomly read; assert match
    read_order = list(data.keys())
    random.shuffle(read_order)
    for k in read_order:
        got = client.get(k)
        assert got is not None, f"Missing key: {k}"
        assert got == data[k], f"Mismatch for {k}: expected {data[k]!r}, got {got!r}"

    # Nonexistent key returns None
    assert client.get("key_nonexistent") is None

    print("All baseline tests passed.")
    sys.exit(0)


if __name__ == "__main__":
    main()
