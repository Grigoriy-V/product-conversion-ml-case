# Online Shoppers split protocol (step 3)

## Frozen holdout validation

The source is the accepted UCI 468 CSV (SHA-256
`b3055ee355f59134d851d32641183cb4a8b45def7124d2f50442a042f358e0d9`).
The model-feature group is the SHA-256 of the ordered raw values of exactly
these 16 allowed columns: `Administrative`, `Administrative_Duration`,
`Informational`, `Informational_Duration`, `ProductRelated`,
`ProductRelated_Duration`, `BounceRates`, `ExitRates`, `SpecialDay`, `Month`,
`OperatingSystems`, `Browser`, `Region`, `TrafficType`, `VisitorType`,
`Weekend`.

Both `Revenue` (target) and `PageValues` (prohibited outcome-conditioned
field) are excluded. The current ignored membership file was checked against
that boundary: 12,205 groups; 0 groups/0 rows cross train/test; and 0
mixed-target groups/0 rows. Consequently no replacement membership was
created and the official source CSV was not changed.

The existing deterministic group-safe, stratified holdout remains frozen:
seed `20260719`, train 9,864 (`FALSE` 8,338; `TRUE` 1,526), test 2,466
(`FALSE` 2,084; `TRUE` 382). Its recorded membership fingerprints are train
`bf86c7bcedc2636d892f4a567d364b04625ae7f8419e177a5e012e7083802d86` and
test `88192976cbf6bcfef812ec1e474b21a019e6f101846701118b2e60070f1ed649`.
The complete membership file SHA-256 is
`8dd85409ff57638ed5a8197cb2d0fe5d1d13ff90c59b6dbd83e08c475e2deee1`.

## Future training-only CV

Model selection will use only the 9,864 frozen training rows. It will create
five validation folds by assigning each target-pure allowed-feature group as a
whole. For each class separately, groups are ordered by descending group size
then SHA-256 of `20260719|label|group_id`; each is placed into the fold with
the fewest rows of that class, then fewest total rows, then SHA-256 of
`20260719|label|group_id|fold` as the tie-breaker. This is deterministic and
leaves every group entirely in either the training or validation side of each
fold.

The focused validation produced fold validation counts: fold 0 = 1,668
`FALSE` / 305 `TRUE`; fold 1 = 1,667 / 305; fold 2 = 1,668 / 305; fold 3 =
1,667 / 306; fold 4 = 1,668 / 305. Future runs must re-check row coverage,
group isolation, nonzero class coverage, and per-class fold range (at most one
row here) before fitting. The held-out 2,466 test rows remain untouched until
the final post-selection evaluation.

When a baseline event is later recorded, the existing ledger vocabulary can
represent this as `baseline_cv.cv.strategy = "GroupKFold"`, `folds = 5`,
`shuffle = true`, `random_state = 20260719`; this report supplies the precise
deterministic group-stratification algorithm without changing the ledger
schema. A standalone completed split-protocol event cannot be appended after
the already-completed `dataset_audit` event because the helper rejects a
repeated operation lifecycle, so no experiment-ledger history was rewritten.

## Evidence

```powershell
python -m unittest tests/test_online_shoppers_split_protocol.py -v
```

The focused test validates membership coverage, the prohibited-feature
boundary, zero crossing/mixed-target groups, deterministic fold assignment,
training-only fold coverage, group isolation, class coverage, class-balance
variation, and membership file hash. No estimator, preprocessor, baseline, or
evaluation was fitted or run.
