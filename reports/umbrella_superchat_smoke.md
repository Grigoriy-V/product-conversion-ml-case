# Umbrella / superchat smoke

## Result

Read-only multi-repository discovery and target-scoped write isolation passed.
Automatic Core sync apply remains intentionally unavailable in Core v0.1; it
was tested as an explicit refusal, not reported as completed.

## Repository discovery

The umbrella directory is not a Git repository. It contained exactly the three
intended repository directories; no unrelated directory required inspection.

| Repository name | Branch / HEAD | Status at discovery | Roadmap | Role and Core pin | Own ledgers |
| --- | --- | --- | --- | --- | --- |
| `human-in-the-loop-ml-orchestration` | `main` / `14b7c2597d1a7e6c57a4ac8c15d3767338c0a27d` | Known unrelated documentation draft | `ORCHESTRATION_ROADMAP.md` | Core `0.1.0` | Agent ledger |
| `My_first_model` | `main` / `5ed6ffb652539bba427cbfb9cbce8522d07ba4b4` | Clean | `ML_PROJECT_ROADMAP.md` | `generative_ml`, Core `0.1.0` at `14b7c25...` | Agent and experiment ledgers |
| `product-conversion-ml-case` | `main` / `ff7ade3fc598685d2488e2cbbc08fd1b14fa084d` | Only this task's started event | `ML_PROJECT_ROADMAP.md`, `PROJECT_ROADMAP.md` | `classical_ml`, Core `0.1.0` at `14b7c25...` | Agent and experiment ledgers |

Each repository has project-local `AGENTS.md` and `.codex/config.toml`.
No event ID occurred in more than one repository ledger. No symlink or reparse
point was found in the checked orchestration paths. The two adapters pass local
self-contained pin/validator checks without requiring a sibling or global Core;
explicit Core-root checks are separate.

Initial state fingerprints:

- Core: `4c69c47d7e7b208c3a666bd6ab98e62ee0179831f023a00629e34eb01dedea9c`
- Generative adapter: `553bc7793f6e32690ea9a0d8dc82c64b9dd47fc89255e90a8884ba028b6f6588`
- Classical adapter after this task's start event:
  `d49bfba35814d52f3303dc7b3b8c0330a1449eb35333e8a0ee40040d8fdaa2e0`

## Sequential sync safety

Core `sync_core.py` ran sequentially:

1. Generative target dry-run: exit `0`, no mutation.
2. Classical target dry-run: exit `0`, no mutation.
3. Classical target `--apply`: intentional exit `2`,
   `v0.1 does not implement apply; no files changed`.

All three state fingerprints remained identical after each command. No sync
command ran concurrently. Apply was not attempted against Core or the
generative adapter.

## Controlled-write isolation

The only intended repository changes from this smoke are this report,
`PROJECT_LOG.md`, and the classical agent ledger. Core and generative status,
HEAD and state fingerprints remained unchanged. Target validators and
`git diff --check` passed.

No dataset, ML operation, network call, commit or push occurred.

## Supervisor closeout

Accepted by `ffca0da0-8fb2-4c88-81fd-e4597e13e57c`. Automatic Core sync apply
remains explicit deferred technical debt. Dataset audit stays gated until the
canonical migration plan decides after lessons promotion and Core freeze.
