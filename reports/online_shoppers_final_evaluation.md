# Online Shoppers step 6: single final frozen-holdout evaluation

The selected fixed `RandomForestClassifier(n_estimators=200, random_state=20260719, n_jobs=-1, min_samples_leaf=2)` was fitted exactly once inside the accepted sklearn Pipeline on all 9,864 frozen training rows. It then materialized and scored the 2,466-row frozen test set once. No model, preprocessing, calibration, or threshold change follows this result.

## Reproducibility and boundary checks

```powershell
.venv\Scripts\python.exe -m unittest tests\test_online_shoppers_final_evaluation.py -v
.venv\Scripts\python.exe audit\online_shoppers_final_evaluation.py --source data\online_shoppers_source\online_shoppers_intention.csv --membership data\frozen_splits\online_shoppers_conversion_v1_membership.csv --output reports\online_shoppers_final_evaluation_results.json
```

The focused test passed 1/1. Runtime was Python 3.12.4 with `numpy==2.2.6`, `pandas==2.3.1`, and `scikit-learn==1.7.0`; final command runtime was 0.735523 s, including a 0.423794 s all-train fit.

- Source SHA-256: `b3055ee355f59134d851d32641183cb4a8b45def7124d2f50442a042f358e0d9`.
- Frozen membership SHA-256: `8dd85409ff57638ed5a8197cb2d0fe5d1d13ff90c59b6dbd83e08c475e2deee1`.
- Verified train/test fingerprints: `bf86c7bcedc2636d892f4a567d364b04625ae7f8419e177a5e012e7083802d86` / `88192976cbf6bcfef812ec1e474b21a019e6f101846701118b2e60070f1ed649`.
- The allowed 16 features exclude both `Revenue` and outcome-conditioned `PageValues`; 12,205 allowed-feature groups had zero split crossings and zero mixed-target groups.

## Held-out result

| metric | final test value |
| --- | ---: |
| Average precision (primary) | 0.368148 |
| ROC-AUC | 0.778014 |
| Balanced accuracy (default threshold 0.5) | 0.521619 |
| Precision (default threshold 0.5) | 0.512821 |
| Recall (default threshold 0.5) | 0.052356 |
| F1 (default threshold 0.5) | 0.095012 |

The default-0.5 confusion matrix with rows/columns `[FALSE, TRUE]` is `[[2065, 19], [362, 20]]`: 19 false positives and 362 false negatives. The model ranks sessions materially above the dummy baseline, but its unmodified default rule identifies only 20 of 382 converting sessions. This is descriptive behavior at a deliberately untuned default threshold, not a recommendation for a product decision rule.

The final AP (0.368148) is slightly below the accepted train-only RF CV mean (0.379083); ROC-AUC is close to its train-CV mean (0.778598). A single holdout need not equal CV exactly, so this comparison is descriptive only and does not trigger a model change.

## Predeclared bounded slices

Only `VisitorType`, `Weekend`, and `Month` were examined, fixed before the run. The machine-readable result contains every group with `n`, positives, prevalence, AP/ROC-AUC where both classes exist, and default-threshold confusion/class behavior.

| slice group | n | positives | AP | ROC-AUC | FP / FN at 0.5 |
| --- | ---: | ---: | ---: | ---: | ---: |
| VisitorType: New_Visitor | 336 | 91 | 0.493147 | 0.740973 | 4 / 81 |
| VisitorType: Returning_Visitor | 2,113 | 285 | 0.324661 | 0.774222 | 15 / 275 |
| VisitorType: Other | 17 | 6 | 0.727778 | 0.727273 | 0 / 6 |
| Weekend: FALSE | 1,902 | 290 | 0.371055 | 0.777877 | 17 / 271 |
| Weekend: TRUE | 564 | 92 | 0.356575 | 0.778510 | 2 / 91 |
| Month: May | 668 | 75 | 0.432508 | 0.814570 | 1 / 72 |
| Month: Nov | 593 | 145 | 0.415607 | 0.723676 | 17 / 132 |
| Month: Feb | 42 | 0 | undefined | undefined | 0 / 0 |

Month groups are small and heterogeneous; the JSON report preserves the remaining month groups but they should not be over-interpreted. `Other` has only 17 rows, and February has one class, so its ranking metrics are correctly reported as undefined. These are bounded descriptive slices, not fairness or production validation.

## Calibration, threshold, and limitations

No probability calibration was performed (`method=none`). The estimator's default 0.5 threshold was retained with no tuning; the ledger represents this honestly with accepted train-CV evidence, not test evidence. The data remain an offline, session-level benchmark: coarse time fields and full-session aggregates do not establish a deployable early-session or real-time predictor. No production claim is made.

Machine-readable evidence: [online_shoppers_final_evaluation_results.json](online_shoppers_final_evaluation_results.json).
