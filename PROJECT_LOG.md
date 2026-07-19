# Project Log

Adapter initialized from Core v0.1; no domain or ML operation has run. See
`reports/bootstrap_classical_adapter.md`.

Adapter acceptance rework added machine-verifiable pin and validated classical
experiment ledger scaffolding; no ML operation ran.

## 2026-07-19 — Independent scaffold acceptance review

Bootstrap-only checks passed, but the Core pin lacks commit/hash evidence and
the classical experiment ledger schema is not enforced. Verdict: **changes
required**. See `reports/classical_scaffold_acceptance_review.md`.

## 2026-07-19 — Classical scaffold rework adversarial review

Routing and human-gate policy are now present, but isolated fixtures show the
Core-pin validator accepts traversal/incomplete coverage and the experiment
ledger accepts malformed/duplicate unsafe records. Verdict remains **changes
required**; see `reports/classical_scaffold_acceptance_review.md`.

## 2026-07-19 — Final classical scaffold technical acceptance

After specialist rework, all 25 tests, validators, and independent adversarial
pin/experiment-ledger fixtures passed. Technical verdict: **accept**. See
`reports/classical_scaffold_acceptance_review.md`.

## 2026-07-19 — Audit-contract acceptance fix

The Core pin and classical experiment ledger were replaced with closed,
fail-closed contracts. The final focused suite passed 25/25 tests, including
isolated adapter validation, full disposable agent lifecycle, Core
tamper/commit/path/link negatives, experiment identity/lifecycle validation,
verified artifact safety, lock cleanup, UTC generation, and byte-identical
rejection. Local and explicit-Core pin validation, both ledger validators,
orchestration validation, and `git diff --check` passed.

Decision: ready for independent supervisor review. No dataset was selected or
downloaded; no model, training, evaluation, benchmark, or other ML operation
ran. `reports/experiment_ledger.jsonl` remains empty.

## 2026-07-19 — Classical scaffold accepted and frozen

Supervisor acceptance event:
`751619d1-93d8-4fff-902f-f2c796f08d63`. The next milestone is the no-ML
Luna/Terra/supervisor portability lifecycle, then umbrella/superchat
verification. Dataset audit remains gated.

## 2026-07-19 — Terra portability smoke

The no-ML Terra scaffold/schema portability smoke passed 25 tests and all
validators. See `reports/portability_smoke.md`. Dataset audit remains gated.

Supervisor accepted the Luna retry and Terra smoke. The next action is
umbrella/superchat verification; dataset work remains gated.

## 2026-07-19 — Umbrella/superchat smoke

Read-only discovery of the three repositories and target-only write isolation
passed. Core sync dry-runs were non-mutating; `--apply` remains intentionally
unavailable. See `reports/umbrella_superchat_smoke.md`.

Supervisor accepted the umbrella smoke in event
`ffca0da0-8fb2-4c88-81fd-e4597e13e57c`. Automatic sync apply remains deferred
technical debt; dataset audit is still gated.
## 2026-07-19 — Classical ML roadmap consolidation

Made `ML_PROJECT_ROADMAP.md` the sole canonical roadmap and removed the
duplicate `PROJECT_ROADMAP.md`. No dataset was selected and no ML, data,
download, or model operation ran.

`python tests/test_classical_scaffold.py -v` passed 3/3. The first isolated
self-contained validation exposed the expected pin mismatch after the
intentional one-line local validator override. With supervisor authorization,
only that validator's target SHA-256 was updated in
`orchestration.lock.json`; Core version, commit, path, source hash, and
`adapted` relationship remain unchanged. The isolated validator suite then
passed 1/1. Local orchestration, Core pin, agent ledger, empty experiment
ledger, roadmap contradiction scan, and `git diff --check` passed.

Decision: hand off dirty for supervisor acceptance; no commit or push.

## 2026-07-19 — Online Shoppers stages 1--3 worker evidence

After recorded human approval, the official UCI 468 source was downloaded only
to ignored `data/` and audited. `Revenue` is the binary session-conversion
target; the local CSV SHA-256 is
`b3055ee355f59134d851d32641183cb4a8b45def7124d2f50442a042f358e0d9`.
The audit found 12,330 rows, 18 columns including target, no missing cells,
125 exact duplicate rows, and `TRUE` prevalence 1,908/12,330 (15.4745%).

`PageValues` was prohibited as an outcome-conditioned Google Analytics metric.
The no-model worker materialized a deterministic duplicate-group-safe,
target-stratified 80/20 holdout (seed 20260719): train 9,864
(`bf86c7bcedc2636d892f4a567d364b04625ae7f8419e177a5e012e7083802d86`) and
test 2,466 (`88192976cbf6bcfef812ec1e474b21a019e6f101846701118b2e60070f1ed649`).
See `reports/online_shoppers_dataset_audit.md` and the append-only experiment
ledger. No fitting, baseline, evaluation, calibration, or threshold operation
ran. Worker recommendation is conditional continue; supervisor review remains
required before the baseline stage.

## 2026-07-19 — Online Shoppers step 3 split protocol validation

The frozen 80/20 membership was rechecked using the accepted allowed-feature
boundary, which excludes both `Revenue` and `PageValues`. All 12,205
allowed-feature groups are isolated to one holdout side; there are zero
crossing and mixed-target groups, so no replacement membership was required.
The focused deterministic group-safe five-fold training-only validation passed;
its concrete protocol and class counts are in
`reports/online_shoppers_split_protocol.md`.

No estimator or preprocessing was fitted and no baseline, evaluation,
calibration, or threshold operation ran. The test membership remains frozen
for final post-selection evaluation. The current experiment-ledger helper
cannot append a separate completed split-review record after a completed
`dataset_audit` operation without violating its immutable lifecycle, so no
experiment-ledger record was added or rewritten. Worker recommendation:
supervisor review for step-3 acceptance.

## 2026-07-19 — Online Shoppers step 4 baseline environment stop

The approved short train-only dummy-versus-logistic baseline did not start:
Python 3.14.2 raised `ModuleNotFoundError: No module named 'sklearn'`, and no
project `.venv`/`venv` was available. No packages were installed. Therefore no
pipeline was constructed or fitted, no folds were evaluated, and no held-out
test row or test membership entered a fitting/evaluation path. See
`reports/online_shoppers_baseline.md`.

Decision: stop/change environment before rerunning the unchanged frozen
train-only protocol; no model comparison conclusion is available.

## 2026-07-19 вЂ” Online Shoppers step 4 baseline completed

A project-local ignored Python 3.12.4 `.venv` was created and installed from
the newly tracked minimal pins: `numpy==2.2.6`, `pandas==2.3.1`, and
`scikit-learn==1.7.0`. The concise import/version smoke passed. The focused
train-boundary test passed 1/1, then the approved baseline command completed
one deterministic five-fold group-safe CV using only the 9,864 frozen train
rows. No held-out row entered `X`, `y`, fit, prediction, or scoring; `Revenue`
and `PageValues` remained excluded.

Both fold-fitted preprocessing pipelines completed. Dummy-prior mean AP was
0.154704 (std 0.000197), ROC-AUC 0.500000, and default-rule balanced accuracy
0.500000. Fixed logistic regression mean AP was 0.330526 (std 0.017620),
ROC-AUC 0.748901 (std 0.007142), and default-rule balanced accuracy 0.512398
(std 0.006811). The default-rule guardrail is not threshold tuning. See
`reports/online_shoppers_baseline.md` and its compact per-fold JSON evidence.

Decision requested: supervisor review; worker recommends continue because the
logistic model improved train-only CV AP by 0.175822 without a detected
protocol violation. No calibration, hyperparameter search, fitted model save,
or held-out test evaluation occurred.

The experiment-ledger append then failed closed: its immutable lifecycle
rejects a completed baseline retry after the previous environment-only failed
baseline event (`invalid repeated operation lifecycle for
online-shoppers-conversion-v1`). The ledger was not bypassed or rewritten.
This is a policy blocker for acceptance; see `reports/online_shoppers_baseline.md`.

## 2026-07-19 — Online Shoppers ledger recovery retry lineage

The failed `online-shoppers-conversion-v1` history was preserved unchanged.
Using the already completed accepted audit/split and train-only baseline
evidence, a compliant retry lineage, `online-shoppers-conversion-v1r1`, now
has completed `dataset_audit` event `88c5c5fe-babd-433d-a888-31fafbe1651d` and
completed `baseline` event `546cd0cc-ecab-4206-9805-90f68a0269a3`.

The baseline record references the existing fixed DummyClassifier-versus-
LogisticRegression five-fold group-safe train-only CV result and its evidence
hashes. No held-out evaluation, calibration, threshold tuning, fitted-model
artifact, or new ML operation is claimed. Both ledger validators and `git
diff --check` passed.

## 2026-07-19 — Online Shoppers step 5 fixed candidate comparison

In the separate candidate lineage `online-shoppers-random-forest-v1`, accepted
audit/split evidence was recorded first, followed by exactly one fixed,
train-only five-fold comparison using the accepted 9,864 rows and 16 allowed
features. No held-out row was materialized for `X`, `y`, fitting, prediction,
or scoring; `Revenue` and `PageValues` remained excluded.

The unchanged Logistic Regression reproduced mean AP 0.330526. The one
predeclared nonlinear candidate, `RandomForestClassifier(n_estimators=200,
random_state=20260719, n_jobs=-1, min_samples_leaf=2)`, achieved mean AP
0.379083 (std 0.009645), ROC-AUC 0.778598, and default-rule balanced accuracy
0.525923. Its AP gain was 0.048557, exceeding the fixed +0.01 selection gate,
so Random Forest is the selected train-only candidate. No tuning, calibration,
threshold adjustment, fitted-model save, error-analysis expansion, or held-out
evaluation occurred. See `reports/online_shoppers_model_comparison.md`.

## 2026-07-19 — Online Shoppers step 6 final frozen-holdout evaluation

The selected fixed Random Forest Pipeline was fit once on all 9,864 frozen
training rows, then the frozen 2,466-row test set was materialized and scored
once. The source, membership, and train/test fingerprints matched accepted
evidence; `Revenue` and `PageValues` stayed excluded, and duplicate-feature
groups remained isolated. The focused final-evaluation test passed 1/1.

Final test AP was 0.368148 and ROC-AUC 0.778014. At the estimator's unchanged
default threshold 0.5, balanced accuracy was 0.521619, precision 0.512821,
recall 0.052356, and F1 0.095012 (19 false positives, 362 false negatives).
Only predeclared `VisitorType`, `Weekend`, and `Month` aggregate slices were
reported. No tuning, model selection, calibration, threshold adjustment, or
test-driven change occurred. See `reports/online_shoppers_final_evaluation.md`
and its JSON evidence. Worker recommends supervisor review; step 7 remains
separate and requires product-need justification before calibration or
threshold work.
## 2026-07-19 — Online Shoppers step 7 train-only threshold analysis

The fixed Random Forest completed one five-fold group-safe OOF run on 9,864 frozen training rows only: `.venv\Scripts\python.exe audit\online_shoppers_threshold_analysis.py --source data\online_shoppers_source\online_shoppers_intention.csv --membership data\frozen_splits\online_shoppers_conversion_v1_membership.csv --output reports\online_shoppers_threshold_analysis_results.json --report reports\online_shoppers_threshold_analysis.md`. Runtime: 2.6348409s.

The pooled-OOF F2-selected threshold was 0.1273247 (F2 0.5833407, precision 0.2538032, recall 0.8636959); default 0.5 was F2 0.0726837, precision 0.5833333, recall 0.0596330. Recall >=0.50/0.60/0.70 points: thresholds 0.2447573/0.2163655/0.1827384; precision 0.3497537/0.3272597/0.2951857; recall 0.5117955/0.6002621/0.7031455. Calibration method: none. No frozen test row, prediction, metric, or final-test artifact was accessed. Events: `a5ffa0b0-3e29-4bf5-b7bd-70f132c2c75c`, `ec62f2e9-8653-4e8a-96f9-f82f4f3d1fa7`, `998d951c-0f73-4a8c-9560-86a7152a2940`.
