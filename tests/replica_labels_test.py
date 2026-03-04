"""
Tests for make_replica_label
- Same (key, replica_id) -> same label every time.
- Different replica_id -> different labels.
- Different keys -> different labels.
- Labels fixed length (same as PRF output).
"""

import sys
sys.path.insert(0, ".")
from crypto_utils import LABEL_LENGTH, make_replica_label


def main() -> None:
    # 1. Same (key, replica_id) produces the same label every time.
    label_user1_0_a = make_replica_label("user1", 0)
    label_user1_0_b = make_replica_label("user1", 0)
    assert label_user1_0_a == label_user1_0_b, "same (key, replica_id) must yield same label"

    # 2. Different replica_id values produce different labels.
    label_user1_0 = make_replica_label("user1", 0)
    label_user1_1 = make_replica_label("user1", 1)
    label_user1_2 = make_replica_label("user1", 2)
    assert label_user1_0 != label_user1_1
    assert label_user1_1 != label_user1_2
    assert label_user1_0 != label_user1_2

    # 3. Different keys produce different labels.
    label_a_0 = make_replica_label("keyA", 0)
    label_b_0 = make_replica_label("keyB", 0)
    assert label_a_0 != label_b_0
    label_a_1 = make_replica_label("keyA", 1)
    label_b_1 = make_replica_label("keyB", 1)
    assert label_a_1 != label_b_1

    # 4. Labels remain fixed length (same as PRF output).
    assert len(label_user1_0_a) == LABEL_LENGTH
    assert len(label_user1_1) == LABEL_LENGTH
    assert len(label_a_0) == LABEL_LENGTH
    assert len(make_replica_label("long_key_name_here", 99)) == LABEL_LENGTH

    print("Replica labels: all checks passed.")


if __name__ == "__main__":
    main()
