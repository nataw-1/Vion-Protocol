"""
Tests — Constitutional Validator
Covers AUTH token validation, timestamp validation, and dry-run enforcement.
"""

import os
import pytest
from unittest.mock import patch
from datetime import datetime, timezone, timedelta

from nvion.core.constitution import ConstitutionValidator


# ─── FIXTURES ─────────────────────────────────────────────────────────────────

@pytest.fixture
def validator(tmp_path):
    """Create a validator with real temp constitutional files."""
    soul = tmp_path / "VION.md"
    identity = tmp_path / "IDENTITY.md"
    soul.write_text("# VION.md — Test Constitution\nVersion: 1.0.0")
    identity.write_text("# IDENTITY.md — Test Registry\nVersion: 1.0.0")
    return ConstitutionValidator(str(soul), str(identity))


# ─── AUTH TOKEN TESTS ─────────────────────────────────────────────────────────

class TestAuthTokenValidation:

    def test_valid_token_passes(self, validator):
        with patch.dict(os.environ, {"VION_AUTH_TOKEN": "test-secret-token"}):
            result = validator.validate_auth_token("test-secret-token")
        assert result["valid"] is True

    def test_wrong_token_fails(self, validator):
        with patch.dict(os.environ, {"VION_AUTH_TOKEN": "real-token"}):
            result = validator.validate_auth_token("wrong-token")
        assert result["valid"] is False
        assert result["condition"] == 1

    def test_empty_token_fails(self, validator):
        with patch.dict(os.environ, {"VION_AUTH_TOKEN": "real-token"}):
            result = validator.validate_auth_token("")
        assert result["valid"] is False
        assert result["condition"] == 1

    def test_none_token_fails(self, validator):
        with patch.dict(os.environ, {"VION_AUTH_TOKEN": "real-token"}):
            result = validator.validate_auth_token(None)
        assert result["valid"] is False

    def test_unconfigured_env_fails(self, validator):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("VION_AUTH_TOKEN", None)
            result = validator.validate_auth_token("any-token")
        assert result["valid"] is False


# ─── TIMESTAMP TESTS ──────────────────────────────────────────────────────────

class TestTimestampValidation:

    def test_fresh_timestamp_passes(self, validator):
        ts = datetime.now(timezone.utc).isoformat()
        result = validator.validate_timestamp(ts)
        assert result["valid"] is True

    def test_expired_timestamp_fails(self, validator):
        old = (datetime.now(timezone.utc) - timedelta(seconds=400)).isoformat()
        with patch.dict(os.environ, {"COMMAND_EXPIRY_SECONDS": "300"}):
            result = validator.validate_timestamp(old)
        assert result["valid"] is False

    def test_future_timestamp_fails(self, validator):
        future = (datetime.now(timezone.utc) + timedelta(seconds=60)).isoformat()
        result = validator.validate_timestamp(future)
        assert result["valid"] is False

    def test_malformed_timestamp_fails(self, validator):
        result = validator.validate_timestamp("not-a-timestamp")
        assert result["valid"] is False

    def test_empty_timestamp_fails(self, validator):
        result = validator.validate_timestamp("")
        assert result["valid"] is False


# ─── DRY RUN TESTS ────────────────────────────────────────────────────────────

class TestDryRunEnforcement:

    def test_dry_run_mode_passes(self, validator):
        with patch.dict(os.environ, {"DRY_RUN_DEFAULT": "TRUE"}):
            result = validator.validate_execution_mode("DRY_RUN")
        assert result["valid"] is True
        assert result["resolved_mode"] == "DRY_RUN"

    def test_live_mode_with_override_passes(self, validator):
        with patch.dict(os.environ, {"DRY_RUN_DEFAULT": "TRUE"}):
            result = validator.validate_execution_mode("LIVE")
        assert result["valid"] is True
        assert result["resolved_mode"] == "LIVE"
        assert result["override"] is True

    def test_unknown_mode_defaults_to_dry_run(self, validator):
        result = validator.validate_execution_mode("UNKNOWN")
        assert result["valid"] is False

    def test_none_mode_defaults_to_dry_run(self, validator):
        with patch.dict(os.environ, {"DRY_RUN_DEFAULT": "TRUE"}):
            result = validator.validate_execution_mode(None)
        assert result["valid"] is True
        assert result["resolved_mode"] == "DRY_RUN"


# ─── INTEGRITY TESTS ──────────────────────────────────────────────────────────

class TestConstitutionalIntegrity:

    def test_integrity_passes_when_files_unchanged(self, validator):
        result = validator.verify_integrity()
        assert result["integrity_valid"] is True
        assert result["condition_6_triggered"] is False

    def test_integrity_fails_when_soul_modified(self, tmp_path):
        soul = tmp_path / "VION.md"
        identity = tmp_path / "IDENTITY.md"
        soul.write_text("# Original VION.md")
        identity.write_text("# Original IDENTITY.md")
        v = ConstitutionValidator(str(soul), str(identity))

        # Tamper with VION.md after loading
        soul.write_text("# TAMPERED VION.md — this should trigger Condition 6")

        result = v.verify_integrity()
        assert result["soul_intact"] is False
        assert result["condition_6_triggered"] is True
