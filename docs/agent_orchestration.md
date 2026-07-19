# Agent orchestration

This document is the standalone operating procedure for this repository. It
does not require policy or instructions from another repository or chat.

## Workflow

1. The supervisor reads `AGENTS.md`, `ML_PROJECT_ROADMAP.md`, relevant reports,
   both ledgers, and Git state.
2. The supervisor defines one bounded task with scope, owned files/artifacts,
   allowed commands, stop conditions, reporting requirements, and acceptance
   criteria.
3. The selected worker appends a `started` event using
   `python tools/agent_ledger.py`, performs only the approved work, and appends
   exactly one terminal `completed`, `failed`, or `interrupted` event.
4. The supervisor checks evidence and ledger validity, then appends `reviewed`
   with the final continue/stop/change/freeze decision.

Workers never set `supervisor_decision`; their lifecycle events use `null`.
Corrections are new append-only events. Timestamps come from system UTC inside
the helper. A helper failure is a stop condition: retain the error and do not
edit JSONL by hand.

A metadata file can be used for a start event:

```powershell
python tools/agent_ledger.py start --metadata-file task-start.json
```

Use the helper's built-in help for the current terminal/review syntax and run
its validation command before handoff. A stale `.lock` sidecar fails closed;
remove it only after confirming no writer process remains.

## Role routing

- `luna_clerk` / `gpt-5.6-luna` / `none`: deterministic clerical extraction,
  formatting, reports, inventories, and supplied-fact ledger operations. No ML
  operations or decisions.
- `terra_worker` / `gpt-5.6-terra` / `low`: normal bounded implementation,
  targeted testing, routine diagnosis, and short validation.
- `sol_specialist` / `gpt-5.6-sol` / `high`: explicit supervisor approval only,
  for complex or high-risk bounded work.

No worker may self-change its model or reasoning, delegate, expand scope, or
change the roadmap. Use one write-heavy worker for overlapping mutable scope.

## Classical ML gates

Before modelling, approve dataset identity/source/license/fingerprint,
observation unit, target and positive class, label timing, prediction-time
feature availability, leakage audit, split strategy and membership, seed,
baseline, metrics, and acceptance criteria. Keep learned preprocessing inside
fold-safe pipelines. Compare candidates on the same frozen splits and
cross-validation protocol. Keep the test set untouched until the approved
final evaluation.

Every material ML action is recorded only through
`tools/experiment_ledger.py` or its documented append API. The event records
the actual command, status, runtime, hashes, metrics, artifacts, and decision.
The worker also updates `PROJECT_LOG.md` and the relevant report. Planned
commands are not completed events.

Long training or evaluation is human-gated. The worker verifies the command,
inputs, expected outputs, resource assumptions, and stop conditions; the user
launches it and returns evidence. Agents must not sleep, poll, or autonomously
continue across that gate.

## Evidence and failure handling

The handoff includes changed files, exact commands, material outputs, hashes,
metrics, skipped checks, known limits, decision requested, and every appended
agent- and experiment-ledger event ID. Never commit secrets, datasets, model
artifacts, caches, or large outputs.

Stop on scope conflict, overlapping writer ownership, ledger/helper failure,
unapproved roadmap or protocol change, missing required data identity, leakage
risk, or an unexpected long-running operation. Preserve evidence and return
control to the supervisor or user.
