# tests/read_then_write_test.py
"""
Tests for read-then-write in BatchEngine.access().
- For a successful access: B reads then B writes to the same labels
- Verify no write back when real label is missing. Instead KeyError.
"""

import sys
sys.path.insert(0, ".")
from batch_engine import BatchEngine
from server import Server


BATCH_SIZE = 3


class RecordServer:
    """Wraps a Server and records the sequence of access and write calls."""

    def __init__(self, server: Server) -> None:
        self._server = server
        self.access_count = 0
        self.write_count = 0
        self._sequence = []  # list of ("access", label) or ("write", label)

    def reset(self) -> None:
        self.access_count = 0
        self.write_count = 0
        self._sequence.clear()

    def access(self, label: bytes) -> bytes:
        self.access_count += 1
        self._sequence.append(("access", label))
        return self._server.access(label)

    def write(self, label: bytes, ciphertext: bytes) -> None:
        self.write_count += 1
        self._sequence.append(("write", label))
        self._server.write(label, ciphertext)

    def read_labels_in_order(self) -> list[bytes]:
        return [label for op, label in self._sequence if op == "access"]

    def write_labels_in_order(self) -> list[bytes]:
        return [label for op, label in self._sequence if op == "write"]


def main() -> None:
    # 1 
    # Successful access: B reads then B writes, same labels same order
    server = Server()
    recorded = RecordServer(server)
    engine = BatchEngine(recorded, batch_size=BATCH_SIZE)

    label = b"test_label_padded_to_32_bytes_12"
    ciphertext = b"x" * 284
    server.write(label, ciphertext)

    recorded.reset()
    result = engine.access(label)

    assert result == ciphertext
    assert recorded.access_count == BATCH_SIZE
    assert recorded.write_count == BATCH_SIZE
    read_labels = recorded.read_labels_in_order()
    write_labels = recorded.write_labels_in_order()
    assert read_labels == write_labels, "write-back must use same labels as reads, same order"
    assert len(read_labels) == BATCH_SIZE
    assert recorded._sequence[:BATCH_SIZE] == [("access", lbl) for lbl in read_labels]
    assert recorded._sequence[BATCH_SIZE:] == [("write", lbl) for lbl in write_labels]


    # 2 
    # Missing real label: KeyError, no write-back
    server2 = Server()
    recorded2 = RecordServer(server2)
    engine2 = BatchEngine(recorded2, batch_size=BATCH_SIZE)
    real_label = b"nonexistent_label_padded_to_32_b"
    recorded2.reset()

    try:
        engine2.access(real_label)
        raise AssertionError("Expected KeyError when real label not found")
    except KeyError as e:
        assert "not found" in str(e).lower()

    assert recorded2.write_count == 0
    assert recorded2.access_count == BATCH_SIZE

    # 3 
    # Real missing with some fake hits: still KeyError, no write-back
    server3 = Server()
    recorded3 = RecordServer(server3)
    engine3 = BatchEngine(recorded3, batch_size=BATCH_SIZE)
    fake_label = b"fake_slot_label_padded_to_32_byt"
    server3.write(fake_label, b"y" * 284)
    real_label3 = b"real_missing_label_padded_to_32b"
    recorded3.reset()

    try:
        engine3.access(real_label3)
        raise AssertionError("Expected KeyError when real label not found")
    except KeyError:
        pass

    assert recorded3.write_count == 0
    assert recorded3.access_count == BATCH_SIZE

    print("All read-then-write tests passed.")


if __name__ == "__main__":
    main()
