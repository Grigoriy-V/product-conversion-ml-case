from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from audit.online_shoppers_split_protocol import (  # noqa: E402
    N_FOLDS,
    deterministic_training_folds,
    fold_summary,
    group_rows,
    load_membership,
    load_rows,
    validate_holdout,
)


class OnlineShoppersSplitProtocolTest(unittest.TestCase):
    def test_frozen_holdout_and_future_cv_are_group_safe_and_deterministic(self) -> None:
        source = ROOT / "data" / "online_shoppers_source" / "online_shoppers_intention.csv"
        membership_path = ROOT / "data" / "frozen_splits" / "online_shoppers_conversion_v1_membership.csv"
        rows, allowed = load_rows(source)
        membership = load_membership(membership_path)
        groups = group_rows(rows, allowed)
        holdout = validate_holdout(rows, groups, membership)

        self.assertEqual(len(allowed), 16)
        self.assertEqual(holdout["crossing_groups"], 0)
        self.assertEqual(holdout["mixed_target_groups"], 0)
        self.assertEqual(holdout["split_class_counts"], {"train": {"FALSE": 8338, "TRUE": 1526}, "test": {"FALSE": 2084, "TRUE": 382}})

        first = deterministic_training_folds(rows, groups, membership)
        second = deterministic_training_folds(rows, groups, membership)
        self.assertEqual(first, second)
        self.assertEqual(set(first), {index for index, split in membership.items() if split == "train"})
        self.assertEqual(set(first.values()), set(range(N_FOLDS)))
        for indices in groups.values():
            training_folds = {first[index] for index in indices if index in first}
            self.assertLessEqual(len(training_folds), 1)
        summary = fold_summary(rows, first)
        for counts in summary.values():
            self.assertGreater(counts["FALSE"], 0)
            self.assertGreater(counts["TRUE"], 0)
        self.assertLessEqual(max(counts["FALSE"] for counts in summary.values()) - min(counts["FALSE"] for counts in summary.values()), 1)
        self.assertLessEqual(max(counts["TRUE"] for counts in summary.values()) - min(counts["TRUE"] for counts in summary.values()), 1)

        self.assertEqual(
            hashlib.sha256(membership_path.read_bytes()).hexdigest(),
            "8dd85409ff57638ed5a8197cb2d0fe5d1d13ff90c59b6dbd83e08c475e2deee1",
        )


if __name__ == "__main__":
    unittest.main()
