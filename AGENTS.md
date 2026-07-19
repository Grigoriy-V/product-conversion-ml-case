# Project Agent Rules

This repository contains its complete local orchestration policy. Agents must
not depend on another repository, chat, checkout, or runtime-inherited policy
to understand or execute work here.

- Before planning an ML experiment, read `ML_PROJECT_ROADMAP.md`. After an
  agreed direction change, update only that file; do not create another
  roadmap.
- After every completed test suite, benchmark, evaluation, training milestone,
  or dataset-preparation milestone, update `PROJECT_LOG.md` and the relevant
  report with commands actually run, material results, and the decision taken.
  Do not log minor intermediate steps.
- Do not commit datasets, fitted models, caches, checkpoints, full generated
  outputs, or other large artifacts. Record hashes and repository-relative
  references instead. Never record secrets.

## Supervisor and worker roles

- The root/main agent is supervisor-only. It reads the roadmap, reports,
  ledgers, metadata, and Git state; defines the bounded next step; writes the
  worker task specification and acceptance criteria; reviews evidence; and
  makes the final continue/stop/change/freeze decision.
- The supervisor must not edit implementation code or experiment
  configurations and must not directly run code inspection, tests, data
  preparation, benchmarks, training, sampling, or evaluation. Delegate those
  actions to a worker.
- Use one primary worker for a write-heavy or ML task. Never run workers
  concurrently against the same files, split, output directory, model
  artifact, or experiment lineage.
- Every worker task must state its scope, owned files and artifacts, permitted
  commands or milestones, required stop conditions, reporting requirements,
  and acceptance criteria. A worker must not broaden scope, change the
  roadmap, change its model or reasoning level, or delegate without supervisor
  approval.
- Long training and evaluation are human-gated. The worker prepares and
  verifies the exact command, expected inputs/outputs, and stop conditions; the
  user launches it and returns the result.

## Agent routing

- Use `luna_clerk` at reasoning `none` only for deterministic clerical work,
  extraction, formatting, reporting, and helper-driven ledger operations.
  Luna must not make project or ML decisions.
- Use `terra_worker` at reasoning `low` for the default bounded
  implementation, targeted tests, routine diagnosis, and short validation.
- Use `sol_specialist` at reasoning `high` only after explicit supervisor
  approval for genuinely complex or high-risk work.

## Agent orchestration and audit

- Profiles are defined in `.codex/agents/`; detailed local procedures are in
  `docs/agent_orchestration.md`.
- Every repository task must append `started`, then exactly one terminal
  `completed`, `failed`, or `interrupted` event through
  `python tools/agent_ledger.py`. Never manually edit, patch, truncate, or
  rewrite `reports/agent_execution_ledger.jsonl`.
- Worker lifecycle events set `supervisor_decision` to `null`. Only the
  supervisor appends a later `reviewed` event with the decision.
- Correct an earlier event by appending a correction event through the helper;
  never alter history. Event timestamps must be captured programmatically from
  system UTC at write time and must never be invented or backdated.
- If `tools/agent_ledger.py` cannot safely append or validate, stop, preserve
  the error evidence, and report failure. Do not bypass the helper.
- The final response must list every agent-ledger event ID appended for the
  task.

## Classical ML protocol

Before modelling, the supervisor must approve and record:

- dataset identity, origin, license or usage basis, immutable fingerprint, and
  storage boundary;
- task definition, observation unit, target, positive class, label timing, and
  prediction-time feature availability;
- leakage and duplicate/group leakage audit;
- split strategy, seed, membership or fingerprints, and the untouched test
  boundary;
- baseline, primary and guardrail metrics, validation protocol, and acceptance
  criteria.

All learned preprocessing must live inside an `sklearn.pipeline.Pipeline` (or
equivalent fold-safe pipeline) and be fitted only on training folds. Model and
hyperparameter comparisons use the same frozen splits and cross-validation
protocol. Report baseline comparisons, uncertainty where appropriate, error
slices, and class-specific behavior. Perform probability calibration or
decision-threshold tuning only when the product decision requires it, using
validation data rather than the test set. Record hashes for finalized split
memberships, configs, data snapshots, and model artifacts.

## Experiment logging

For every material ML operation that actually runs, including data
preparation, audit, split creation, benchmark, smoke test, training,
evaluation, comparison, artifact freeze, or experiment closeout:

- append an event only through `python tools/experiment_ledger.py` or its
  documented append API; never manually edit, patch, insert, truncate, or
  rewrite `reports/experiment_ledger.jsonl`;
- record actual status, exact command, runtime context, hashes, metrics,
  artifacts, and resulting continue/stop/change/freeze decision as applicable;
- distinguish completed, failed, skipped, and pending work; never present a
  planned command as completed;
- capture timestamps programmatically from system UTC;
- stop and report failure if the helper/API cannot safely append or validate;
- list every appended experiment-ledger event ID in the final response.

The worker that runs a material operation is responsible for its ledger event,
`PROJECT_LOG.md`, and relevant report. The supervisor verifies all three before
accepting the milestone.
