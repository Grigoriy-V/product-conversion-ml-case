# Classical ML scaffold acceptance review

## Verdict

**Changes required.** The repository is a clean lightweight bootstrap, but it
does not yet provide the required machine-verifiable Core pin or enforce the
classical experiment contract.

## Blocking findings

1. `orchestration.lock.json` records only Core version, adapter type, and
   adapter name. It has no Core repository/commit, no manifest, and no hashes;
   therefore no validator can verify the intended Core source or detect drift.
   A manifest-tamper negative test is unavailable because no manifest exists.

2. `tools/validate_orchestration.py` does not inspect either
   `reports/experiment_ledger.jsonl` or `reports/experiment_ledger.schema.json`.
   In an isolated target copy, an experiment record with an unknown status and
   wrong nested type was accepted by that validator. Thus the supplied schema
   is parsed only as data, not enforced.

3. The classical experiment schema lists the requested top-level fields, but
   its nested objects are unconstrained: it does not require sklearn Pipeline
   identity/configuration, CV/baseline/calibration/threshold detail, artifact
   path safety, hashes, or a meaningful decision contract. `AGENTS.md` also
   omits the project-specific supervisor-only and human-gated ML/logging rules;
   it retains only generic Core markers and placeholder adapter-local text.

## Passed evidence

- Target is independent Git `main`, with no commit and no remote; all scaffold
  content is intentionally untracked pre-acceptance.
- `.gitignore` allowlists `.codex/config.toml` and agent profiles, while
  excluding runtime state, data, outputs, artifacts, models, and common large
  classical artifacts.
- Two bundled scaffold tests passed; orchestration validator and target agent
  ledger validation passed. An isolated full helper lifecycle including review
  validated successfully.
- No local paths, secrets, symlinks/reparse points, data/model files, or large
  artifacts were found. No dataset, training, evaluation, download, or model
  content is present beyond placeholders.

## Scope

No ML operation, data download, network action, commit, or push occurred.

## Rework adversarial review — 2026-07-19

### Verdict: changes required

The project policy now correctly states supervisor-only control and the exact
semi-automatic human gate. The Core pin and experiment helper remain unsafe,
however:

1. `tools/validate_core_pin.py` validates only the entries present. It has no
   lock schema, no required critical-file coverage, no duplicate/unknown-entry
   check, and no safe-path/resolve containment. An isolated one-entry lock
   with `target_path: ../outside.txt` and a matching hash returned success.

2. `tools/experiment_ledger.py` does not enforce its bundled schema vocabulary
   beyond a shallow manual shape check. An isolated append accepted an invalid
   timestamp, malformed nested Pipeline object, artifact path through an
   escaping symlink, non-hex artifact hash, and a duplicate `event_id`.
   It does not generate UTC itself, validate artifacts exist or resolve within
   the project, or enforce experiment identity/lifecycle. Empty nested runtime
   and modelling evidence also satisfy a completed event.

3. The three bundled tests pass but do not exercise those failure paths; they
   are insufficient acceptance evidence for a material ML audit ledger.

Passed checks: target agent lifecycle works in isolation; three bundled tests,
target validators, and `git diff --check` passed. No data/model/large artifact
or reparse point was present; `.gitignore` and routing profiles are correct.

## Final specialist-rework technical review — 2026-07-19

### Verdict: accept

All 25 target tests and every validator passed. Independent temporary fixtures
also confirmed the repaired contracts:

- the 13-file Core pin rejects traversal, incomplete/extra/duplicate/unknown
  mappings, relation/hash mismatch, target tamper, and linked files or parents;
- local pin validation needs no sibling Core, while explicit Core validation
  verifies the pinned commit/version and managed hashes even when unrelated
  mutable Core documentation is dirty;
- the experiment helper generates UUIDv4 and system UTC, validates all existing
  JSONL before append, rejects caller-generated IDs/timestamps, duplicate
  identity/order, empty or malformed runtime/Pipeline/CV/calibration/threshold
  evidence, and unsafe/missing/linked/hash-mismatched artifacts;
- stale/concurrent locks fail closed without byte mutation, validation failures
  clean their locks, and successful appends are EOF-only with cleanup.

The repository remains a no-data/no-model scaffold on independent Git `main`
with no commit or remote. No ML, download, network, commit, or push occurred.
Core and generative repositories were read-only during this review.

## Final audit-contract rework — 2026-07-19

### Worker verdict

**Ready for independent supervisor review.** This is worker evidence only; the
worker did not append a supervisor decision and did not accept the milestone.

### Implemented contract

The Core pin now has a closed lock schema and exactly 13 immutable/bootstrap
control mappings. Target and Core paths are unique, canonical repository
relative paths; missing, duplicate, extra, or unknown mappings fail. Files and
all parents must be regular, contained, and free of symlinks, junctions, or
other reparse points. Hashes are lowercase SHA-256. `exact_copy` requires equal
target/Core hashes, while `adapted` requires distinct hashes and the approved
mapping. Local validation is self-contained; `--core-root` additionally checks
Core `VERSION`, the exact 40-hex Git commit, and each source hash. Mutable logs,
JSONL evidence, and adapter-owned experiment files are not pinned.

The experiment helper now generates UUIDv4 IDs and system UTC timestamps; an
append caller cannot supply either. It takes an atomic sidecar lock before
opening the ledger, validates every prior JSONL record plus the candidate, and
rejects duplicate IDs, non-increasing timestamps, dataset identity drift,
stage regression, unresolved pending stages, missing prerequisites, and
post-closeout events. Validation errors remove the sidecar without changing
ledger bytes. Existing locks fail closed. An uncertain append retains the lock
for the documented manual crash-recovery procedure.

The `bundled-classical-v2` validator enforces closed status/operation contracts.
Completed stages require exact commands, runtime, strict dataset/source/
license/target/fingerprint identity, meaningful decision and rationale, plus
stage-relevant leakage/split/feature, sklearn Pipeline/baseline/CV/metrics, or
calibration/threshold evidence. Pending, skipped, and failed records cannot
fabricate results. Every artifact must be a present regular non-link file
inside the repository and match its recorded SHA-256.

### Commands and results

- `python -m py_compile tools/validate_core_pin.py tools/experiment_ledger.py tools/validate_orchestration.py tests/test_core_pin.py tests/test_ledgers.py tests/test_agent_lifecycle.py tests/test_self_contained.py`
  — passed.
- `python -m unittest discover -s tests -v`
  — 25 tests passed, 0 failures, 0 skips.
- `python tools/validate_core_pin.py`
  — passed locally with 13 managed files.
- `python tools/validate_core_pin.py --core-root D:/ML/human-in-the-loop-ml-orchestration`
  — passed VERSION, exact commit, and all 13 source hashes. The Core worktree's
  unrelated documentation changes did not alter pinned files.
- `python tools/experiment_ledger.py validate`
  — passed with 0 events.
- `python tools/agent_ledger.py validate`
  — passed before the worker terminal event.
- `python tools/validate_orchestration.py`
  — passed.
- `git diff --check`
  — passed. The repository still has no initial commit, so all scaffold files
  remain untracked and the command has no tracked diff to inspect.
- The focused suite's isolated-copy test copied the adapter without `.git` or
  caches and ran all four local validators successfully. Its disposable agent
  ledger completed `started -> completed -> reviewed` without touching target
  evidence.
- A repository scan found no reparse points, files over 1 MiB, datasets,
  models, checkpoints, caches, or generated ML artifacts. Private/absolute
  path matches were limited to intentional validator and negative-test
  patterns.

### Changed files

`.gitignore`; `core/orchestration_lock.schema.json`;
`docs/architecture.md`; `docs/classical_ml_adapter.md`;
`docs/lesson_promotion.md`; `docs/lifecycle.md`;
`docs/multi_repo_supervision.md`; `docs/project_adapter_contract.md`;
`orchestration.lock.json`; `PROJECT_LOG.md`;
`reports/agent_execution_ledger.jsonl`;
`reports/classical_scaffold_acceptance_review.md`;
`reports/experiment_ledger.schema.json`;
`tests/test_agent_lifecycle.py`; `tests/test_classical_scaffold.py`;
`tests/test_core_pin.py`; `tests/test_ledgers.py`;
`tests/test_self_contained.py`; `tools/experiment_ledger.py`;
`tools/validate_core_pin.py`; and `tools/validate_orchestration.py`.

### Stop conditions and limits

No approved stop condition was encountered. No managed Core drift was found.
No network, commit, push, dataset selection/download, model implementation,
training, benchmark, sampling, or evaluation occurred. The semi-automatic
human gate remains unchanged.

The schema JSON files describe the enforced bundled vocabularies but do not
claim complete support for any JSON Schema Draft; the Python validators are
authoritative. Artifact validation proves current contained bytes and hashes,
not external provenance. A process crash during the single-record append can
leave an uncertain tail; the retained lock deliberately requires human
inspection rather than automatic repair or JSONL rewriting.

## Supervisor closeout

Accepted by supervisor event `751619d1-93d8-4fff-902f-f2c796f08d63`.
The scaffold is frozen. The next action is a no-ML portability lifecycle smoke
(Luna deterministic task, Terra scaffold/schema task, supervisor review),
followed by umbrella/superchat verification. Dataset audit remains gated.
