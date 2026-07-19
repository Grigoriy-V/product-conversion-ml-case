# Classical ML adapter

This adapter owns dataset identity and fingerprinting, target definition,
license evidence, leakage audit, split strategy, feature schema, sklearn
Pipeline structure, baseline and cross-validation evidence, calibration,
threshold selection, artifacts, and the resulting decision. No dataset
selection, download, training, or evaluation is authorized until the human
approves the applicable gate.

## Enforced experiment contract

`tools/experiment_ledger.py` is the authoritative validator for the exact
`bundled-classical-v2` vocabulary described in
`reports/experiment_ledger.schema.json`. It intentionally does not claim a
complete JSON Schema Draft implementation.

- Callers provide a closed evidence object and cannot provide `event_id` or
  `timestamp_utc`; the helper generates a UUIDv4 and system UTC timestamp.
- Every append validates the entire existing JSONL history plus the candidate.
  IDs and timestamps are unique/ordered, dataset identity cannot drift within
  one experiment, stages cannot regress, and closeout is terminal.
- Completed stages require exact commands, runtime evidence, strict dataset
  identity, a meaningful decision, and the evidence specific to that stage.
  Failed, skipped, and pending events use their separate closed contracts and
  cannot claim result-bearing fields.
- Artifact paths are canonical repository-relative POSIX paths. Each artifact
  must already be a regular non-link file inside the project and its lowercase
  SHA-256 must match its current bytes.

The helper acquires `<ledger>.lock` atomically before opening the ledger. A
concurrent or stale lock fails closed and is never auto-removed. Normal
completion and validation failures remove their lock. A process crash or an
uncertain write deliberately leaves the lock in place: confirm that no writer
process remains, preserve and inspect the lock metadata, validate the JSONL,
and remove the sidecar manually only if the ledger has a complete valid tail.
If the tail is incomplete or corrupt, stop and escalate; never rewrite JSONL
history to conceal the failure.

## Core pin contract

`tools/validate_core_pin.py` locally verifies the closed lock schema, exact
critical bootstrap-control coverage, unique safe paths, file and parent
link/reparse rejection, strict hashes, target containment, and exact/adapted
relationship semantics. `--core-root` additionally verifies Core `VERSION`,
the pinned Git commit, and every Core source hash. Mutable evidence and
adapter-owned experiment files are deliberately excluded from the Core pin.
