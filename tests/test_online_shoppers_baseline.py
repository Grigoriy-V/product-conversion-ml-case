from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from audit.online_shoppers_baseline import load_train_only, validate_folds


class OnlineShoppersBaselineTest(unittest.TestCase):
    def test_train_only_group_safe_baseline_protocol(self) -> None:
        source = ROOT / "data" / "online_shoppers_source" / "online_shoppers_intention.csv"
        membership = ROOT / "data" / "frozen_splits" / "online_shoppers_conversion_v1_membership.csv"
        X, y, folds, evidence = load_train_only(source, membership)
        self.assertEqual((len(X), len(y), len(folds)), (9864, 9864, 9864))
        self.assertNotIn("Revenue", X.columns)
        self.assertNotIn("PageValues", X.columns)
        self.assertEqual(evidence["test_rows_materialized_for_modeling"], 0)
        result = validate_folds(y, folds)
        self.assertTrue(result["validation_coverage_once"])
        self.assertTrue(result["group_isolation"])
