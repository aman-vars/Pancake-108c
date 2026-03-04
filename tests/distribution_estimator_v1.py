# tests/distribution_estimator_v1.py
"""
Tests for DistributionEstimator
- Insert keys, access some keys multiple times.
- Verify distribution sums to 1.
- Verify heavier keys have larger π'.
"""

import sys
sys.path.insert(0, ".")

from proxy import Proxy
from distribution_estimator import DistributionEstimator
from server import Server
from client import Client


def main() -> None:
    server = Server()
    calculator = DistributionEstimator()
    proxy = Proxy(server, distribution_estimator=calculator)
    client = Client(proxy)

    # Insert keys 'a', 'b', 'c'
    client.put("a", "v1")
    client.put("b", "v2")
    client.put("c", "v3")

    # Access some keys multiple times (3 'a', 2 'b', 1 'c')
    client.get("a")
    client.get("a")
    client.get("a")
    client.get("b")
    client.get("b")
    client.get("c")

    # total_accesses: 3 PUTs + 6 GETs = 9
    assert calculator.total_accesses() == 9, f"expected 9, got {calculator.total_accesses()}"

    pi = calculator.get_distribution()
    # a: 1P + 3G = 4, b: 1P + 2G = 3, c: 1P + 1G = 2
    assert abs(sum(pi.values()) - 1.0) < 1e-9, f"normalized distribution must sum to 1, got {sum(pi.values())}"

    # Hotter keys have larger π'
    assert pi["a"] > pi["b"], "a accessed more than b, so π'(a) > π'(b)"
    assert pi["b"] > pi["c"], "b accessed more than c, so π'(b) > π'(c)"

    # Exact expected frequencies: 4/9, 3/9, 2/9
    assert abs(pi["a"] - 4 / 9) < 1e-9
    assert abs(pi["b"] - 3 / 9) < 1e-9
    assert abs(pi["c"] - 2 / 9) < 1e-9

    print("DistributionEstimator: all checks passed.")


if __name__ == "__main__":
    main()
