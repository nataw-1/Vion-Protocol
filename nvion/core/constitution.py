"""
N VION Protocol — Constitutional Validator
Layer 1: Validates all commands and actions against VION.md rules.
"""

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path


class ConstitutionValidator:
    """
    Reads VION.md and IDENTITY.md and enforces constitutional rules.
    Every command passes through here before reaching the Orchestrator.
    """

    def __init__(self, soul_path: str, identity_path: str):
        self.soul_path = Path(soul_path)
        self.identity_path = Path(identity_path)
        self._soul_hash = None
        self._identity_hash = None
        self._load_constitution()

    # ─── LOAD & INTEGRITY CHECK ───────────────────────────────────────────────

    def _load_constitution(self):
        """Load constitutional documents and record their hashes for integrity."""
        if not self.soul_path.exists():
            raise FileNotFoundError(
                f"CRITICAL: VION.md not found at {self.soul_path}. "
                "System cannot start without the constitution."
            )
        if not self.identity_path.exists():
            raise FileNotFoundError(
                f"CRITICAL: IDENTITY.md not found at {self.identity_path}. "
                "System cannot start without the identity registry."
            )

        self._soul_hash = self._hash_file(self.soul_path)
        self._identity_hash = self._hash_file(self.identity_path)

    def _hash_file(self, path: Path) -> str:
        """SHA-256 hash of a file for integrity tracking."""
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def verify_integrity(self) -> dict:
        """
        Check that constitutional documents have not been modified
        since system start. Condition 6 trigger if tampered.
        """
        current_soul_hash = self._hash_file(self.soul_path)
        current_identity_hash = self._hash_file(self.identity_path)

        soul_intact = current_soul_hash == self._soul_hash
        identity_intact = current_identity_hash == self._identity_hash

        return {
            "soul_intact": soul_intact,
            "identity_intact": identity_intact,
            "integrity_valid": soul_intact and identity_intact,
            "condition_6_triggered": not (soul_intact and identity_intact),
        }

    # ─── AUTH TOKEN VALIDATION ────────────────────────────────────────────────

    def validate_auth_token(self, provided_token: str) -> dict:
        """
        Validates the AUTH token against the configured Owner secret.
        Condition 1 trigger if invalid.
        """
        expected_token = os.getenv("VION_AUTH_TOKEN", "")

        if not provided_token:
            return {
                "valid": False,
                "reason": "No AUTH token provided.",
                "condition": 1,
            }

        if not expected_token:
            return {
                "valid": False,
                "reason": "VION_AUTH_TOKEN not configured in environment.",
                "condition": 1,
            }

        # Constant-time comparison to prevent timing attacks
        token_valid = hmac_compare(provided_token, expected_token)

        if not token_valid:
            return {
                "valid": False,
                "reason": "AUTH token is invalid. Command source not authorized.",
                "condition": 1,
            }

        return {"valid": True, "reason": "AUTH token validated."}

    # ─── COMMAND TIMESTAMP VALIDATION ─────────────────────────────────────────

    def validate_timestamp(self, timestamp_str: str) -> dict:
        """
        Rejects commands older than the configured expiry window.
        Prevents replay attacks.
        """
        expiry_seconds = int(os.getenv("COMMAND_EXPIRY_SECONDS", "300"))

        try:
            command_time = datetime.fromisoformat(timestamp_str).replace(
                tzinfo=timezone.utc
            )
        except (ValueError, TypeError):
            return {
                "valid": False,
                "reason": f"Invalid timestamp format: {timestamp_str}",
            }

        now = datetime.now(timezone.utc)
        age_seconds = (now - command_time).total_seconds()

        if age_seconds > expiry_seconds:
            return {
                "valid": False,
                "reason": (
                    f"Command expired. Age: {int(age_seconds)}s, "
                    f"Max allowed: {expiry_seconds}s."
                ),
            }

        if age_seconds < 0:
            return {
                "valid": False,
                "reason": "Command timestamp is in the future. Rejected.",
            }

        return {"valid": True, "reason": "Timestamp valid.", "age_seconds": age_seconds}

    # ─── DRY RUN ENFORCEMENT ──────────────────────────────────────────────────

    def validate_execution_mode(self, mode: str) -> dict:
        """
        Enforces dry-run default per VION.md Section 3.4.
        LIVE execution requires explicit declaration.
        """
        dry_run_default = os.getenv("DRY_RUN_DEFAULT", "TRUE").upper() == "TRUE"
        mode = (mode or "DRY_RUN").upper()

        if mode not in ("DRY_RUN", "LIVE"):
            return {
                "valid": False,
                "reason": f"Unknown execution mode: {mode}. Must be DRY_RUN or LIVE.",
                "resolved_mode": "DRY_RUN",
            }

        if mode == "LIVE" and dry_run_default:
            # LIVE is allowed but must be explicitly declared — log the override
            return {
                "valid": True,
                "reason": "LIVE mode explicitly declared. Dry-run default overridden.",
                "resolved_mode": "LIVE",
                "override": True,
            }

        return {
            "valid": True,
            "reason": f"Execution mode: {mode}.",
            "resolved_mode": mode,
            "override": False,
        }


# ─── UTILITY ──────────────────────────────────────────────────────────────────

def hmac_compare(a: str, b: str) -> bool:
    """Constant-time string comparison to prevent timing attacks."""
    import hmac
    return hmac.compare_digest(a.encode(), b.encode())
