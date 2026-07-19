"""Validate the adapter's immutable Core provenance contract.

Local validation is self-contained: it verifies the closed lock shape, exact
critical-file coverage, path safety, relationship semantics, and target hashes.
Passing ``--core-root`` additionally verifies the pinned Core checkout's
VERSION, Git commit, and managed source hashes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "orchestration.lock.json"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
REPARSE_POINT = 0x400

# These are the executable/bootstrap controls copied from Core. Adapter-owned
# experiment files and mutable evidence are intentionally not Core-managed.
CRITICAL_MANAGED_FILES: dict[str, tuple[str, str]] = {
    "AGENTS.md": ("AGENTS.md", "adapted"),
    ".codex/config.toml": (".codex/config.toml", "exact_copy"),
    ".codex/agents/luna_clerk.toml": (
        ".codex/agents/luna_clerk.toml",
        "adapted",
    ),
    ".codex/agents/sol_specialist.toml": (
        ".codex/agents/sol_specialist.toml",
        "adapted",
    ),
    ".codex/agents/terra_worker.toml": (
        ".codex/agents/terra_worker.toml",
        "adapted",
    ),
    "tools/agent_ledger.py": ("tools/agent_ledger.py", "exact_copy"),
    "tools/validate_orchestration.py": (
        "tools/validate_orchestration.py",
        "adapted",
    ),
    "reports/agent_execution_ledger.schema.json": (
        "reports/agent_execution_ledger.schema.json",
        "exact_copy",
    ),
    "core/task_spec.schema.json": (
        "core/task_spec.schema.json",
        "exact_copy",
    ),
    "core/project_manifest.schema.json": (
        "core/project_manifest.schema.json",
        "exact_copy",
    ),
    "docs/agent_orchestration.md": (
        "docs/agent_orchestration.md",
        "adapted",
    ),
    "requirements.txt": ("requirements.txt", "exact_copy"),
    "VERSION": ("VERSION", "exact_copy"),
}

LOCK_KEYS = {
    "core_repository",
    "core_version",
    "core_commit",
    "adapter_type",
    "managed_files",
}
ENTRY_KEYS = {
    "target_path",
    "target_sha256",
    "core_path",
    "core_sha256",
    "relationship",
}


class PinError(ValueError):
    """The Core provenance contract is invalid."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_reparse(path: Path) -> bool:
    info = path.lstat()
    return path.is_symlink() or bool(
        getattr(info, "st_file_attributes", 0) & REPARSE_POINT
    )


def _validate_relative_path(value: Any, field: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise PinError(f"{field} must be a non-empty relative path")
    if "\\" in value or ":" in value:
        raise PinError(f"{field} must use canonical repository-relative POSIX syntax")
    relative = PurePosixPath(value)
    if (
        relative.is_absolute()
        or value != relative.as_posix()
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        raise PinError(f"unsafe {field}: {value!r}")
    return relative


def _regular_contained_file(root: Path, value: str, field: str) -> Path:
    relative = _validate_relative_path(value, field)
    root = root.absolute()
    if not root.is_dir() or _is_reparse(root):
        raise PinError(f"{field} root is missing or is a link/reparse point")

    current = root
    for part in relative.parts:
        current = current / part
        try:
            if _is_reparse(current):
                raise PinError(f"{field} traverses a link/reparse point: {value}")
        except FileNotFoundError as exc:
            raise PinError(f"{field} is missing: {value}") from exc

    try:
        resolved_root = root.resolve(strict=True)
        resolved = current.resolve(strict=True)
        resolved.relative_to(resolved_root)
    except (OSError, ValueError) as exc:
        raise PinError(f"{field} escapes its repository: {value}") from exc
    if not stat.S_ISREG(resolved.stat().st_mode):
        raise PinError(f"{field} is not a regular file: {value}")
    return resolved


def _load_lock(lock_path: Path) -> dict[str, Any]:
    try:
        raw = lock_path.read_text(encoding="utf-8")
        lock = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PinError(f"cannot read Core pin: {exc}") from exc
    if not isinstance(lock, dict) or set(lock) != LOCK_KEYS:
        raise PinError("Core pin must be a closed object with the required fields")
    if lock["core_repository"] != "human-in-the-loop-ml-orchestration":
        raise PinError("unexpected Core repository identity")
    if not isinstance(lock["core_version"], str) or not VERSION_RE.fullmatch(
        lock["core_version"]
    ):
        raise PinError("core_version must be semantic x.y.z")
    if not isinstance(lock["core_commit"], str) or not COMMIT_RE.fullmatch(
        lock["core_commit"]
    ):
        raise PinError("core_commit must be a lowercase 40-hex Git object id")
    if lock["adapter_type"] != "classical_ml":
        raise PinError("adapter_type must be classical_ml")
    if not isinstance(lock["managed_files"], list):
        raise PinError("managed_files must be an array")
    return lock


def validate_pin(
    *,
    root: Path = ROOT,
    lock_path: Path | None = None,
    core_root: Path | None = None,
) -> dict[str, Any]:
    """Validate and return the closed Core pin."""

    root = root.absolute()
    lock_path = lock_path or root / "orchestration.lock.json"
    lock = _load_lock(lock_path)
    entries = lock["managed_files"]
    if len(entries) != len(CRITICAL_MANAGED_FILES):
        raise PinError("managed_files does not have exact critical-file coverage")

    by_target: dict[str, dict[str, Any]] = {}
    seen_core_paths: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != ENTRY_KEYS:
            raise PinError("each managed-file entry must be a closed object")
        target_path = entry["target_path"]
        core_path = entry["core_path"]
        _validate_relative_path(target_path, "target_path")
        _validate_relative_path(core_path, "core_path")
        if target_path in by_target:
            raise PinError(f"duplicate target_path: {target_path}")
        if core_path in seen_core_paths:
            raise PinError(f"duplicate core_path: {core_path}")
        if not isinstance(entry["target_sha256"], str) or not SHA256_RE.fullmatch(
            entry["target_sha256"]
        ):
            raise PinError(f"invalid target SHA-256 for {target_path}")
        if not isinstance(entry["core_sha256"], str) or not SHA256_RE.fullmatch(
            entry["core_sha256"]
        ):
            raise PinError(f"invalid Core SHA-256 for {target_path}")
        by_target[target_path] = entry
        seen_core_paths.add(core_path)

    if set(by_target) != set(CRITICAL_MANAGED_FILES):
        missing = sorted(set(CRITICAL_MANAGED_FILES) - set(by_target))
        unknown = sorted(set(by_target) - set(CRITICAL_MANAGED_FILES))
        raise PinError(f"managed-file coverage mismatch; missing={missing}; unknown={unknown}")

    for target_path, (expected_core_path, expected_relationship) in (
        CRITICAL_MANAGED_FILES.items()
    ):
        entry = by_target[target_path]
        if (
            entry["core_path"] != expected_core_path
            or entry["relationship"] != expected_relationship
        ):
            raise PinError(f"invalid managed-file relationship for {target_path}")
        same_hash = entry["target_sha256"] == entry["core_sha256"]
        if expected_relationship == "exact_copy" and not same_hash:
            raise PinError(f"exact_copy hashes differ for {target_path}")
        if expected_relationship == "adapted" and same_hash:
            raise PinError(f"adapted file must differ from Core: {target_path}")

        target_file = _regular_contained_file(root, target_path, "target_path")
        if sha256_file(target_file) != entry["target_sha256"]:
            raise PinError(f"target hash mismatch: {target_path}")

    if core_root is not None:
        core_root = core_root.absolute()
        version_file = _regular_contained_file(core_root, "VERSION", "Core VERSION")
        if version_file.read_text(encoding="utf-8").strip() != lock["core_version"]:
            raise PinError("Core VERSION does not match the pin")
        try:
            commit = subprocess.run(
                ["git", "-C", os.fspath(core_root), "rev-parse", "--verify", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
                timeout=10,
            ).stdout.strip()
        except (OSError, subprocess.SubprocessError) as exc:
            raise PinError(f"cannot verify Core Git commit: {exc}") from exc
        if commit != lock["core_commit"]:
            raise PinError("Core Git commit does not match the pin")

        for target_path, entry in by_target.items():
            source = _regular_contained_file(
                core_root, entry["core_path"], "core_path"
            )
            if sha256_file(source) != entry["core_sha256"]:
                raise PinError(f"Core source hash mismatch: {target_path}")

    return lock


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--lock", type=Path)
    parser.add_argument("--core-root", type=Path)
    args = parser.parse_args(argv)
    try:
        lock = validate_pin(
            root=args.root,
            lock_path=args.lock,
            core_root=args.core_root,
        )
    except PinError as exc:
        print(f"error: invalid Core pin: {exc}", file=sys.stderr)
        return 2
    mode = "local+Core" if args.core_root else "local"
    print(
        f"valid: Core pin ({mode}, {len(lock['managed_files'])} managed files)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
