# Classical ML Adapter Rules

The root agent is supervisor-only: it reads the canonical `ML_PROJECT_ROADMAP.md`,
defines bounded work, reviews evidence, and decides continue/stop/change/freeze.
Workers perform code, tests, and ML work. Use project-local profiles and
`tools/agent_ledger.py`; worker events never decide.

Before modelling, the supervisor must approve dataset identity, target,
leakage audit and split strategy. `reports/experiment_ledger.jsonl` is
append-only and `tools/experiment_ledger.py` is mandatory for material
operations. Long ML is semi-automatic: a worker prepares the exact command,
the user launches it; no autonomous training, evaluation, or sleep/wait.

Do not record secrets or commit datasets, models, caches, outputs or large
artifacts. This adapter adds these rules to Core lifecycle/routing; it does not
replace them.
