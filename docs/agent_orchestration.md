# Agent orchestration

This is the Core entrypoint. Read [architecture](architecture.md) for the Core
boundary, [lifecycle](lifecycle.md) for ledger events,
[multi-repository supervision](multi_repo_supervision.md) for umbrella-chat
boundaries, [the adapter contract](project_adapter_contract.md) for local
ownership, and [lesson promotion](lesson_promotion.md) for controlled reuse.

Use a metadata file for the first ledger event:

```powershell
python tools/agent_ledger.py start --metadata-file task-start.json
```

Core v0.1 uses a bundled validator for the schema vocabulary shipped here
(`required`, types, properties, arrays, enums, patterns, constants and the
conditional forms used by the ledger). It is not a claim of full Draft 2020-12
implementation. A stale `.lock` sidecar fails closed; remove it only after
confirming no writer process remains.
