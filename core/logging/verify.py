"""
Verify tamper-proof JSONL audit logs.

Usage:
    python -m core.logging.verify logs/agent_actions.jsonl
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from .agent_logger import GENESIS_HASH, compute_entry_hash


@dataclass(frozen=True)
class VerificationResult:
    """Result of checking one JSONL audit log file."""

    ok: bool
    checked_entries: int
    error: str | None = None


def verify_log_file(path: str | Path) -> VerificationResult:
    """Verify every hashed entry in a JSONL audit log."""
    log_path = Path(path)
    if not log_path.exists():
        return VerificationResult(False, 0, f"file not found: {log_path}")

    previous_hash: str | None = None
    checked = 0

    for line_no, raw_line in enumerate(log_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue

        try:
            entry = json.loads(line)
        except json.JSONDecodeError as exc:
            return VerificationResult(False, checked, f"line {line_no}: invalid JSON: {exc}")

        entry_hash = entry.get("entry_hash")
        prev_hash = entry.get("prev_hash")
        if not isinstance(entry_hash, str) or not entry_hash:
            return VerificationResult(False, checked, f"line {line_no}: missing entry_hash")
        if not isinstance(prev_hash, str) or not prev_hash:
            return VerificationResult(False, checked, f"line {line_no}: missing prev_hash")

        expected_hash = compute_entry_hash(entry)
        if entry_hash != expected_hash:
            return VerificationResult(False, checked, f"line {line_no}: hash mismatch")

        if previous_hash is not None and prev_hash != previous_hash:
            return VerificationResult(False, checked, f"line {line_no}: prev_hash mismatch")

        previous_hash = entry_hash
        checked += 1

    return VerificationResult(True, checked)


def upgrade_log_file(path: str | Path) -> VerificationResult:
    """Rewrite a legacy JSONL log file with prev_hash/entry_hash fields."""
    log_path = Path(path)
    if not log_path.exists():
        return VerificationResult(False, 0, f"file not found: {log_path}")

    upgraded_lines: list[str] = []
    previous_hash = GENESIS_HASH
    checked = 0

    for line_no, raw_line in enumerate(log_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue

        try:
            entry = json.loads(line)
        except json.JSONDecodeError as exc:
            return VerificationResult(False, checked, f"line {line_no}: invalid JSON: {exc}")

        entry["prev_hash"] = previous_hash
        entry["entry_hash"] = compute_entry_hash(entry)
        previous_hash = entry["entry_hash"]
        upgraded_lines.append(json.dumps(entry, ensure_ascii=False))
        checked += 1

    log_path.write_text("\n".join(upgraded_lines) + ("\n" if upgraded_lines else ""), encoding="utf-8")
    return verify_log_file(log_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify JSONL audit log hash chain.")
    parser.add_argument(
        "--upgrade",
        action="store_true",
        help="Rewrite a legacy JSONL log with prev_hash/entry_hash fields before verifying.",
    )
    parser.add_argument("log_file", help="Path to JSONL audit log file")
    args = parser.parse_args()

    result = upgrade_log_file(args.log_file) if args.upgrade else verify_log_file(args.log_file)
    if result.ok:
        print(f"✅ Chain intact ({result.checked_entries} entries)")
        return 0

    print(f"❌ Chain broken after {result.checked_entries} entries: {result.error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
