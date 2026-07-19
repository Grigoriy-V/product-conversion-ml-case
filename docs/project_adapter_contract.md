# Project policy contract

This repository is operationally self-contained. Its checked-in `AGENTS.md`,
`.codex/config.toml`, `.codex/agents/`, schemas, helpers, documentation,
roadmap, logs, and ledgers define the complete local agent contract. Runtime
inheritance from a parent checkout, shared chat, or another repository is
neither required nor assumed.

`orchestration.lock.json` records provenance for selected files. An
`exact_copy` relationship means the local bytes match the pinned source hash;
an `adapted` relationship means the local file intentionally differs while
retaining its recorded source hash. Provenance is not live policy inheritance:
agents execute the local checked-in files.

Local validation must check path safety, relationship semantics, target hashes,
and the immutable recorded source hashes. Updating an adapted policy changes
only its target hash and relationship when necessary; it must not silently
change the pinned source commit or source hash. Any future synchronization is
an explicit reviewed repository change, never an automatic runtime dependency.
