# Online Shoppers conversion: dataset, leakage, and split audit

## Approved scope and provenance

Human approval covers the **UCI Online Shoppers Purchasing Intention Dataset** (UCI id 468), with one row treated as one session and `Revenue` as the binary purchase-conversion target (`TRUE` is positive). The official UCI record identifies the source CSV, says the dataset has 12,330 sessions and 17 features, and licenses it CC BY 4.0: <https://archive.ics.uci.edu/dataset/468/online%2Bshoppers%2Bpurchasing%2Bintention%2Bdataset>. The downloaded official archive was obtained from <https://archive.ics.uci.edu/static/public/468/online+shoppers+purchasing+intention+dataset.zip>.

The local ignored source `data/online_shoppers_source/online_shoppers_intention.csv` has SHA-256 `b3055ee355f59134d851d32641183cb4a8b45def7124d2f50442a042f358e0d9`. The machine-readable result is [online_shoppers_dataset_audit.json](online_shoppers_dataset_audit.json).

## Reproducible audit facts

- Schema: 12,330 rows and 18 columns (17 candidate features plus `Revenue`); the exact ordered schema is recorded in the JSON evidence.
- All CSV cells are strings on disk. UCI describes 10 numeric attributes and 8 categorical attributes including the target; the semantic column roles are recorded in the evidence.
- Missing cells: 0 in every column. Exact duplicate full rows: 125.
- Target: `FALSE` 10,422 (84.5255%) and `TRUE` 1,908 (15.4745%). This is an imbalanced binary-classification task.
- The UCI documentation says the data were formed so each session belongs to a different user during a one-year period. There is no user/session identifier in the file, so that assertion cannot be independently checked locally and no user IDs are inferred.

## Prediction point and leakage decision

The intended use is an **in-session, pre-conversion decision**: after the visitor has generated the observed browsing prefix and immediately before a purchase decision/outcome is known. It is not a pre-session propensity model. A deployment must compute each included session aggregate only from actions already observed at that point.

`Revenue` is prohibited as a feature. `PageValues` is excluded and prohibited: UCI defines Page Value as the average value of a page visited before completing an e-commerce transaction. That makes it a post-outcome / transaction-conditioned Google Analytics metric for this target and too risky to use in an honest conversion prediction.

The included numeric features are `Administrative`, `Administrative_Duration`, `Informational`, `Informational_Duration`, `ProductRelated`, `ProductRelated_Duration`, `BounceRates`, `ExitRates`, and `SpecialDay`. The included categorical features are `Month`, `OperatingSystems`, `Browser`, `Region`, `TrafficType`, `VisitorType`, and `Weekend`. UCI says the page-category values are derived from URLs and updated as actions occur. Bounce Rate and Exit Rate are Google Analytics page metrics; they are included only for the defined in-session point, with the operational requirement that their values be available without using the current session's final outcome.

There is no exact event timestamp or page-event sequence, only coarse `Month` and `Weekend`, so temporal precedence and production feature availability cannot be proven from this file. Full-session count/duration aggregates also cannot support a strict early-session prediction claim; a later model report must keep the in-session prediction-point limitation explicit and, if production requirements are stricter, change to prefix/event-level data. There are no campaign/user identifiers for a real group split. The duplicate-content audit found 12,205 distinct non-target feature vectors and no feature-identical vector with conflicting target; the frozen split keeps every such vector wholly on one side to avoid duplicate-profile contamination.

## Frozen holdout

The split is materialized only in ignored `data/frozen_splits/online_shoppers_conversion_v1_membership.csv`; no data rows are tracked. It is a deterministic 80/20 randomized, target-stratified holdout, seed `20260719`. For each target class, the algorithm uses `random.Random(20260719)`, shuffles whole target-pure groups of identical non-target features in sorted target-label order, and chooses whole groups summing exactly to `round(class_count * 0.20)`.

- Train: 9,864 rows (`FALSE` 8,338; `TRUE` 1,526), fingerprint `bf86c7bcedc2636d892f4a567d364b04625ae7f8419e177a5e012e7083802d86`.
- Test: 2,466 rows (`FALSE` 2,084; `TRUE` 382), fingerprint `88192976cbf6bcfef812ec1e474b21a019e6f101846701118b2e60070f1ed649`.

The test membership and its fingerprints are frozen before any model selection. No model, dummy baseline, transformer fitting, evaluation, calibration, or threshold work occurred.

## Commands and worker recommendation

```powershell
Invoke-WebRequest -Uri 'https://archive.ics.uci.edu/static/public/468/online+shoppers+purchasing+intention+dataset.zip' -OutFile data\online_shoppers_purchasing_intention_dataset.zip
Expand-Archive -LiteralPath data\online_shoppers_purchasing_intention_dataset.zip -DestinationPath data\online_shoppers_source -Force
python audit\online_shoppers_audit.py --source data\online_shoppers_source\online_shoppers_intention.csv --report reports\online_shoppers_dataset_audit.json --split data\frozen_splits\online_shoppers_conversion_v1_membership.csv
python -m unittest tests\test_online_shoppers_audit.py -v
```

Worker recommendation: **continue**, conditionally. The source/license/schema and split are suitable for a constrained, explicitly in-session benchmark that excludes `PageValues`; the supervisor should retain the feature-availability limitation and approve the frozen protocol before any baseline stage. This is evidence and a worker recommendation, not a supervisor decision.
