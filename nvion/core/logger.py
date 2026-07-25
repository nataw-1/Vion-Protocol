"""
N VION Protocol — Activity Logger
Append-only with hash-linked integrity chain.

Every log entry contains:
  - A SHA-256 hash of its own content
  - The hash of the previous entry (chain link)

This makes the log tamper-evident. If any entry is modified,
every entry after it has a broken chain — provable in court.
"""

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

from .exceptions import LogIntegrityError


class EventType(str, Enum):
    COMMAND_RECEIVED    = "COMMAND_RECEIVED"
    COMMAND_REJECTED    = "COMMAND_REJECTED"
    COMMAND_VALIDATED   = "COMMAND_VALIDATED"
    TASK_DISPATCHED     = "TASK_DISPATCHED"
    AGENT_SUSPENDED     = "AGENT_SUSPENDED"
    AGENT_REACTIVATED   = "AGENT_REACTIVATED"
    AUDIT_PASS          = "AUDIT_PASS"
    AUDIT_BLOCK         = "AUDIT_BLOCK"
    HALT_TRIGGERED      = "HALT_TRIGGERED"
    ESCALATE_TRIGGERED  = "ESCALATE_TRIGGERED"
    SYSTEM_START        = "SYSTEM_START"
    SYSTEM_HALT         = "SYSTEM_HALT"
    INTEGRITY_CHECK     = "INTEGRITY_CHECK"
    DRY_RUN_OVERRIDE    = "DRY_RUN_OVERRIDE"
    CONSTITUTION_VALID  = "CONSTITUTION_VALID"


def _hash_entry(content: str, prev_hash: str) -> str:
    """SHA-256 hash of content + previous hash. This is the chain link."""
    raw = f"{prev_hash}:{content}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


GENESIS_HASH = hashlib.sha256(b"N-VION-PROTOCOL-GENESIS").hexdigest()


class ActivityLogger:
    """
    Append-only hash-linked activity logger.

    Each entry is a JSON line with two extra fields:
      entry_hash  — SHA-256(this entry content + prev_hash)
      prev_hash   — hash of the previous entry (GENESIS_HASH for first entry)

    To verify the chain:
        logger.verify_chain()  → returns True if intact, raises LogIntegrityError if broken
    """

    def __init__(self, log_path: str):
        self.log_path = Path(log_path)
        self._session_id = str(uuid.uuid4())[:8].upper()
        self._prev_hash = self._load_last_hash()
        self._ensure_log_dir()

    def _ensure_log_dir(self):
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_path.exists():
            self.log_path.touch()

    def _load_last_hash(self) -> str:
        """Load the hash of the last log entry to continue the chain."""
        log_path = Path(self.log_path) if not isinstance(self.log_path, Path) else self.log_path
        if not log_path.exists():
            return GENESIS_HASH
        lines = log_path.read_text(encoding="utf-8").strip().splitlines()
        if not lines:
            return GENESIS_HASH
        try:
            last = json.loads(lines[-1])
            return last.get("entry_hash", GENESIS_HASH)
        except (json.JSONDecodeError, KeyError):
            return GENESIS_HASH

    def _write(self, entry: dict):
        """
        Hash and append a single log entry.
        The chain: entry_hash = SHA256(entry_content + prev_entry_hash)
        """
        # Remove hash fields before computing (they're added after)
        content_for_hash = {k: v for k, v in entry.items()
                            if k not in ("entry_hash", "prev_hash")}
        content_str = json.dumps(content_for_hash, sort_keys=True, ensure_ascii=False)

        entry_hash = _hash_entry(content_str, self._prev_hash)
        entry["prev_hash"] = self._prev_hash
        entry["entry_hash"] = entry_hash
        self._prev_hash = entry_hash

        line = json.dumps(entry, ensure_ascii=False) + "\n"
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(line)

    def _base_entry(self, event_type: EventType) -> dict:
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": self._session_id,
            "event_type": event_type.value,
            "deployment": os.getenv("DEPLOYMENT_NAME", "N-VION"),
        }

    # ─── VERIFY CHAIN ─────────────────────────────────────────────────────────

    def verify_chain(self) -> bool:
        """
        Verify the entire log chain from genesis.
        Returns True if intact.
        Raises LogIntegrityError if any entry has been tampered with.

        How it works:
        - Re-computes each entry's hash from its content + previous hash
        - Compares against the stored entry_hash
        - Any mismatch = tampering detected at that index
        """
        if not self.log_path.exists():
            return True

        lines = self.log_path.read_text(encoding="utf-8").strip().splitlines()
        if not lines:
            return True

        prev = GENESIS_HASH
        for i, line in enumerate(lines):
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                raise LogIntegrityError(i)

            stored_hash = entry.get("entry_hash", "")
            stored_prev = entry.get("prev_hash", "")

            if stored_prev != prev:
                raise LogIntegrityError(i)

            content_for_hash = {k: v for k, v in entry.items()
                                if k not in ("entry_hash", "prev_hash")}
            content_str = json.dumps(content_for_hash, sort_keys=True, ensure_ascii=False)
            expected_hash = _hash_entry(content_str, prev)

            if expected_hash != stored_hash:
                raise LogIntegrityError(i)

            prev = stored_hash

        return True

    # ─── LOG METHODS ──────────────────────────────────────────────────────────

    def log_system_start(self):
        entry = self._base_entry(EventType.SYSTEM_START)
        entry["message"] = "N VION Protocol Orchestrator started."
        self._write(entry)

    def log_command_received(self, raw_command: dict, source: str = "CLI"):
        entry = self._base_entry(EventType.COMMAND_RECEIVED)
        entry["source"] = source
        entry["target"] = raw_command.get("target", "UNKNOWN")
        entry["action"] = raw_command.get("action", "UNKNOWN")
        entry["mode"] = raw_command.get("mode", "UNKNOWN")
        entry["has_auth_token"] = bool(raw_command.get("auth_token"))
        self._write(entry)

    def log_command_rejected(self, reason: str, condition: int = 0, raw_command: dict = None):
        entry = self._base_entry(EventType.COMMAND_REJECTED)
        entry["reason"] = reason
        entry["condition_triggered"] = condition
        if raw_command:
            entry["target"] = raw_command.get("target", "UNKNOWN")
            entry["action"] = raw_command.get("action", "UNKNOWN")
        self._write(entry)

    def log_command_validated(self, command: dict):
        entry = self._base_entry(EventType.COMMAND_VALIDATED)
        entry["target"] = command.get("target")
        entry["action"] = command.get("action")
        entry["mode"] = command.get("mode")
        self._write(entry)

    def log_task_dispatched(self, agent_id: str, agent_name: str, action: str, mode: str):
        entry = self._base_entry(EventType.TASK_DISPATCHED)
        entry["agent_id"] = agent_id
        entry["agent_name"] = agent_name
        entry["action"] = action
        entry["mode"] = mode
        self._write(entry)

    def log_agent_suspended(self, agent_id: str, agent_name: str, reason: str, condition: int):
        entry = self._base_entry(EventType.AGENT_SUSPENDED)
        entry["agent_id"] = agent_id
        entry["agent_name"] = agent_name
        entry["reason"] = reason
        entry["condition"] = condition
        self._write(entry)

    def log_agent_reactivated(self, agent_id: str, agent_name: str):
        entry = self._base_entry(EventType.AGENT_REACTIVATED)
        entry["agent_id"] = agent_id
        entry["agent_name"] = agent_name
        self._write(entry)

    def log_audit_pass(self, agent_id: str, action: str):
        entry = self._base_entry(EventType.AUDIT_PASS)
        entry["agent_id"] = agent_id
        entry["action"] = action
        self._write(entry)

    def log_audit_block(self, agent_id: str, action: str, reason: str):
        entry = self._base_entry(EventType.AUDIT_BLOCK)
        entry["agent_id"] = agent_id
        entry["action"] = action
        entry["reason"] = reason
        self._write(entry)

    def log_halt(self, condition: int, reason: str, agents_suspended: list = None):
        entry = self._base_entry(EventType.HALT_TRIGGERED)
        entry["condition"] = condition
        entry["reason"] = reason
        entry["agents_suspended"] = agents_suspended or []
        entry["severity"] = "CRITICAL"
        self._write(entry)

    def log_escalate(self, condition: int, reason: str, agent_id: str = None):
        entry = self._base_entry(EventType.ESCALATE_TRIGGERED)
        entry["condition"] = condition
        entry["reason"] = reason
        entry["agent_id"] = agent_id
        entry["severity"] = "WARNING"
        self._write(entry)

    def log_integrity_check(self, soul_intact: bool, identity_intact: bool):
        entry = self._base_entry(EventType.INTEGRITY_CHECK)
        entry["soul_md_intact"] = soul_intact
        entry["identity_md_intact"] = identity_intact
        entry["result"] = "PASS" if (soul_intact and identity_intact) else "FAIL"
        self._write(entry)

    def log_dry_run_override(self, target: str, action: str):
        entry = self._base_entry(EventType.DRY_RUN_OVERRIDE)
        entry["target"] = target
        entry["action"] = action
        entry["message"] = "LIVE mode override — dry-run default bypassed by Owner."
        self._write(entry)

    def log_system_halt(self, reason: str):
        entry = self._base_entry(EventType.SYSTEM_HALT)
        entry["reason"] = reason
        entry["message"] = "Full system HALT. All agents suspended. Awaiting Owner restart."
        self._write(entry)

    # ─── READ ─────────────────────────────────────────────────────────────────

    def read_recent(self, n: int = 20) -> list:
        if not self.log_path.exists():
            return []
        lines = self.log_path.read_text(encoding="utf-8").strip().splitlines()
        recent = lines[-n:] if len(lines) >= n else lines
        entries = []
        for line in reversed(recent):
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return entries

    def read_halts(self) -> list:
        if not self.log_path.exists():
            return []
        results = []
        for line in self.log_path.read_text(encoding="utf-8").strip().splitlines():
            try:
                entry = json.loads(line)
                if entry.get("event_type") in (
                    EventType.HALT_TRIGGERED.value,
                    EventType.SYSTEM_HALT.value,
                ):
                    results.append(entry)
            except json.JSONDecodeError:
                continue
        return results

    @property
    def session_id(self) -> str:
        return self._session_id
