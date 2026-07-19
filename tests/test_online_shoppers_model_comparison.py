from __future__ import annotations

import sys
import unittest
from pathlib import Path

from sklearn.ensemble import RandomForestClassifier

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from audit.online_shoppers_model_comparison import RF_CONFIG, make_models
from audit.online_shoppers_baseline import load_train_only, validate_folds


class OnlineShoppersModelComparisonTest(unittest.TestCase):
    def test_fixed_candidate_and_train_only_protocol(self) -> None:
        models = make_models()
        rf = models["random_forest"].named_steps["model"]
        self.assertIsInstance(rf, RandomForestClassifier)
        self.assertEqual(rf.get_params(deep=False)["random_state"], 20260719)
        self.assertEqual(rf.get_params(deep=False)["n_estimators"], 200)
        self.assertEqual(rf.get_params(deep=False)["n_jobs"], -1)
        self.assertEqual(rf.get_params(deep=False)["min_samples_leaf"], 2)
        source = ROOT / "data" / "online_shoppers_source" / "online_shoppers_intention.csv"
        membership = ROOT / "data" / "frozen_splits" / "online_shoppers_conversion_v1_membership.csv"
        X, y, folds, evidence = load_train_only(source, membership)
        self.assertEqual((len(X), len(y), len(folds)), (9864, 9864, 9864))
        self.assertNotIn("Revenue", X.columns)
        self.assertNotIn("PageValues", X.columns)
        self.assertEqual(evidence["test_rows_materialized_for_modeling"], 0)
        checks = validate_folds(y, folds)
        self.assertTrue(checks["validation_coverage_once"])
        self.assertTrue(checks["group_isolation"])
