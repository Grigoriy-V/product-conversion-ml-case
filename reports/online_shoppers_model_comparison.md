# Online Shoppers step 5: fixed candidate comparison

This is a separate candidate baseline lineage, `online-shoppers-random-forest-v1`.
It uses only the accepted 9,864 frozen training rows and exact deterministic
five-fold allowed-feature-group-safe assignments. No held-out row entered `X`,
`y`, fit, prediction, or scoring; `Revenue` and `PageValues` were excluded.

## Predeclared candidates

The accepted `LogisticRegression(max_iter=1000, solver="lbfgs")` was reproduced
unchanged. The single nonlinear candidate was fixed before execution as
`RandomForestClassifier(n_estimators=200, random_state=20260719, n_jobs=-1,
min_samples_leaf=2)`. Two hundred trees is a bounded short CPU budget;
`n_jobs=-1` uses the available CPU cores for that bounded run; `min_samples_leaf=2`
is a conservative fixed regularizer to reduce single-leaf variance. These are
not tuned values. Both candidates retain the accepted fold-fitted
`Pipeline`/`ColumnTransformer` boundary: numeric median imputation and
`StandardScaler`; categorical most-frequent imputation and
`OneHotEncoder(handle_unknown="ignore")`.

The focused protocol test passed 1/1, confirming the fixed RF configuration,
the 16-feature boundary, 9,864 train-only rows, zero test rows materialized
for modelling, exact validation coverage once, and group isolation.

## One train-only CV run

```powershell
.venv\Scripts\python.exe -m unittest tests\test_online_shoppers_model_comparison.py -v
.venv\Scripts\python.exe audit\online_shoppers_model_comparison.py --source data\online_shoppers_source\online_shoppers_intention.csv --membership data\frozen_splits\online_shoppers_conversion_v1_membership.csv --output reports\online_shoppers_model_comparison_results.json
```

| model | fold AP | mean AP ± std | mean ROC-AUC ± std | mean balanced accuracy ± std | CV runtime |
| --- | --- | --- | --- | --- | --- |
| Logistic regression | 0.319918, 0.315596, 0.329079, 0.364642, 0.323397 | 0.330526 ± 0.017620 | 0.748901 ± 0.007142 | 0.512398 ± 0.006811 | 0.312015 s |
| Random Forest | 0.368307, 0.366312, 0.386519, 0.386509, 0.387768 | 0.379083 ± 0.009645 | 0.778598 ± 0.006729 | 0.525923 ± 0.004577 | 1.929650 s |

Balanced accuracy is at each estimator's default decision rule; it was neither
used to tune a threshold nor used for model selection. The logistic fit emitted
five non-fatal sklearn/scipy `OptimizeWarning: Unknown solver options: iprint`
messages, as in the accepted baseline; all fits and metrics completed finite.

## Selection

The fixed rule was: select Random Forest only if its mean AP exceeds accepted
Logistic Regression mean AP `0.33052640487158447` by at least `0.01` absolute;
otherwise retain Logistic Regression for simplicity. RF mean AP was
`0.37908310923231386`, an absolute gain of `0.04855670436072939`; therefore
the selected train-only candidate is **Random Forest**. This is not a held-out
test result and neither calibration nor threshold tuning was performed.

Machine-readable per-fold metrics and protocol evidence are in
`reports/online_shoppers_model_comparison_results.json`; total command runtime
was `2.444509` seconds.

## Worker recommendation

Continue to supervisor review with Random Forest as the selected candidate for
the later single final holdout evaluation. Do not access the held-out test
before that decision is accepted.
