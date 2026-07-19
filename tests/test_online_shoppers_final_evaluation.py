from __future__ import annotations

import sys
import unittest
from pathlib import Path

from sklearn.ensemble import RandomForestClassifier

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from audit.online_shoppers_final_evaluation import DEFAULT_THRESHOLD, RF_CONFIG, SLICE_COLUMNS, make_model


class OnlineShoppersFinalEvaluationTest(unittest.TestCase):
    def test_fixed_pipeline_and_predeclared_analysis_scope(self) -> None:
        model = make_model()
        forest = model.named_steps["model"]
        self.assertIsInstance(forest, RandomForestClassifier)
        self.assertEqual(forest.get_params(deep=False), {**forest.get_params(deep=False), **RF_CONFIG})
        self.assertEqual(DEFAULT_THRESHOLD, 0.5)
        self.assertEqual(SLICE_COLUMNS, ("VisitorType", "Weekend", "Month"))
        self.assertEqual(model.named_steps["preprocess"].transformers[0][1].named_steps["imputer"].strategy, "median")
        self.assertEqual(model.named_steps["preprocess"].transformers[1][1].named_steps["onehot"].handle_unknown, "ignore")


if __name__ == "__main__":
    unittest.main()
