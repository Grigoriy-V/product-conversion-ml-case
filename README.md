# Online Shoppers Conversion Prediction

A practical classical-ML portfolio case: rank website sessions by purchase intent while keeping leakage controls, model selection, and decision-threshold trade-offs explicit.

**Selected result:** a fixed Random Forest reached **0.368 AP** on one frozen holdout, versus a **0.155 AP** dummy-prior baseline. Average precision (AP) is the primary metric because purchases are the minority class (15.5%).

![Average precision comparison](docs/assets/model_ap_comparison.svg)

The final holdout was opened once after model selection. Its AP (0.368) is close to the selected train-only five-fold CV mean (0.379); this is descriptive evidence, not a statistical-significance or production claim.

## Problem and data

The task is binary session-level conversion prediction: estimate whether a session ends with `Revenue=TRUE`. The data are the [UCI Online Shoppers Purchasing Intention Dataset](https://archive.ics.uci.edu/dataset/468/online+shoppers+purchasing+intention+dataset) (UCI id 468, CC BY 4.0): 12,330 sessions, 1,908 purchases, and 18 original columns. The accepted CSV fingerprint is recorded in the [dataset audit](reports/online_shoppers_dataset_audit.md).

This is an offline benchmark, not evidence of a deployable real-time or early-session predictor.

## Protocol that protects the result

- `Revenue` is the label and is never a feature. `PageValues` is excluded as an outcome-conditioned analytics field.
- Exact duplicate-feature groups are kept on one split side. The frozen group-safe, stratified split uses seed `20260719`: 9,864 train rows and 2,466 held-out rows.
- Numeric/categorical preprocessing and each estimator live inside an sklearn `Pipeline` and are fitted only within training folds.
- Dummy prior, Logistic Regression, and the single fixed Random Forest candidate use the same five-fold group-safe training CV. The Random Forest cleared the predeclared AP-improvement gate and was fitted once on all training rows before final testing.

## Main evidence

| Evidence | AP | ROC-AUC | Boundary |
| --- | ---: | ---: | --- |
| Dummy prior | 0.155 | 0.500 | five-fold train CV |
| Logistic Regression | 0.331 | 0.749 | five-fold train CV |
| Selected Random Forest | 0.379 | 0.779 | five-fold train CV |
| Selected Random Forest | 0.368 | 0.778 | one frozen holdout |

At the estimator’s untouched default threshold of 0.5, the holdout recall is only 5.2% (20 of 382 conversions). That does not contradict its ranking metrics; it shows why a product decision needs an explicit threshold rule.

![Threshold operating-point trade-off](docs/assets/threshold_tradeoff.svg)

The figure uses **train-only out-of-fold (OOF)** predictions. The illustrative F2-selected point (`0.127`) prioritizes missed conversions: recall 86.4%, precision 25.4%, and 52.6% of sessions flagged. It is not calibrated probability output or a production cost policy. The frozen test was not used to select it.

## Evidence map

- [Dataset and leakage audit](reports/online_shoppers_dataset_audit.md)
- [Frozen split protocol](reports/online_shoppers_split_protocol.md)
- [Baseline evidence](reports/online_shoppers_baseline.md)
- [Fixed candidate comparison](reports/online_shoppers_model_comparison.md)
- [Single final holdout evaluation](reports/online_shoppers_final_evaluation.md)
- [Train-only threshold analysis](reports/online_shoppers_threshold_analysis.md)
- [Portfolio case study](docs/portfolio_case_study.md)
- [Project log](PROJECT_LOG.md) and [roadmap](ML_PROJECT_ROADMAP.md)

## Reproduce the portfolio figures

No dataset download, model fitting, or test access is required for this cheap path. From PowerShell:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe tools\build_portfolio_figures.py
.venv\Scripts\python.exe -m unittest tests\test_portfolio_figures.py -v
```

The script reads only the accepted compact JSON evidence under `reports/` and regenerates PNG/SVG files under `docs/assets/`.

## Scope and next phase

Scores are not calibrated probabilities. The threshold analysis is an illustrative validation-only decision rule, not a deployed policy. Aggregate session fields mean the case does not prove early-session availability, real-time performance, causal impact, or fairness.

A future model-improvement phase is planned but **has not run**. Since the final test has already been used once, new candidates may be compared on the frozen training CV protocol, but an unbiased new final claim needs a separate independent external dataset or a newly frozen evaluation boundary.
