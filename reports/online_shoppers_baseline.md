# Online Shoppers step 4 baseline

## Environment recovery

A project-local ignored `.venv` was created with Python 3.12.4. The tracked
minimal baseline requirements are exactly `numpy==2.2.6`, `pandas==2.3.1`, and
`scikit-learn==1.7.0`; their import smoke passed at those exact versions.

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -c "import sys, sklearn, pandas, numpy; print('python='+sys.version.split()[0]); print('sklearn='+sklearn.__version__); print('pandas='+pandas.__version__); print('numpy='+numpy.__version__)"
```

## Frozen train-only CV result

The completed baseline command was:

```powershell
.venv\Scripts\python.exe audit\online_shoppers_baseline.py --source data\online_shoppers_source\online_shoppers_intention.csv --membership data\frozen_splits\online_shoppers_conversion_v1_membership.csv --output reports\online_shoppers_baseline_results.json
```

It materialized exactly 9,864 frozen train rows (`FALSE` 8,338; `TRUE` 1,526)
and no held-out row in `X`, `y`, fit, predict, or scoring. `Revenue` and
`PageValues` were excluded. The deterministic group-safe assignments covered
every train row once: validation folds 0--4 respectively had
`FALSE/TRUE` counts of 1668/305, 1667/305, 1668/305, 1667/306, and 1668/305;
all group-isolation and finite-metric checks passed.

Both estimators used fold-fitted sklearn `Pipeline`s. Preprocessing was a
`ColumnTransformer`: median imputation and `StandardScaler` for the nine
numeric columns; most-frequent imputation and
`OneHotEncoder(handle_unknown='ignore')` for the seven categorical columns.
The estimators were `DummyClassifier(strategy='prior')` and fixed
`LogisticRegression(max_iter=1000, solver='lbfgs')`. No calibration,
threshold tuning, hyperparameter search, extra model family, fitted-model
save, or held-out evaluation occurred.

| model | fold AP | mean AP ± std | mean ROC-AUC ± std | mean balanced accuracy ± std | total CV runtime |
| --- | --- | --- | --- | --- | --- |
| Dummy prior | 0.154587, 0.154665, 0.154587, 0.155094, 0.154587 | 0.154704 ± 0.000197 | 0.500000 ± 0.000000 | 0.500000 ± 0.000000 | 0.169421 s |
| Logistic regression | 0.319918, 0.315596, 0.329079, 0.364642, 0.323397 | 0.330526 ± 0.017620 | 0.748901 ± 0.007142 | 0.512398 ± 0.006811 | 0.339367 s |

Balanced accuracy is at the estimator's default decision rule and is not a
tuned threshold result. During logistic fitting, sklearn/scipy emitted five
non-fatal `OptimizeWarning: Unknown solver options: iprint` messages; all five
fits completed and all recorded metrics were finite.

Machine-readable per-fold evidence: `reports/online_shoppers_baseline_results.json`.

## Worker recommendation

**Continue to supervisor review.** Logistic regression improved mean average
precision by 0.175822 (0.330526 versus 0.154704) without a detected protocol
violation. This is a train-only CV comparison, not a held-out test result.

## Ledger blocker

The material run could not be recorded as a completed `baseline` event. The
append-only helper rejected the safe retry because its lifecycle validator does
not permit `baseline: completed` after the earlier environment-only
`baseline: failed` event: `invalid repeated operation lifecycle for
online-shoppers-conversion-v1`. The ledger was not edited or bypassed. Under
the repository policy, this blocks acceptance until the supervisor authorizes
a ledger-contract remedy or another compliant path.
