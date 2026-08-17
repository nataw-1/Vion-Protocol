"""
Tests — Log Integrity Chain
Verifies that hash-linked logs detect tampering correctly.
"""

import json
import pytest
from pathlib import Path

from nvion.core.logger import ActivityLogger, GENESIS_HASH
from nvion.core.exceptions import LogIntegrityError


@pytest.fixture
def logger(tmp_path):
    return ActivityLogger(str(tmp_path / "test.log"))


class TestLogIntegrityChain:

    def test_fresh_log_verifies_clean(self, logger):
        logger.log_system_start()
        logger.log_command_received({"target": "VION-RSC-001", "action": "test", "mode": "DRY_RUN"})
        assert logger.verify_chain() is True

    def test_chain_links_correctly(self, logger):
        logger.log_system_start()
        logger.log_system_start()
        logger.log_system_start()

        lines = logger.log_path.read_text().strip().splitlines()
        entries = [json.loads(l) for l in lines]

        # First entry's prev_hash must be GENESIS_HASH
        assert entries[0]["prev_hash"] == GENESIS_HASH
        # Each entry's prev_hash must match the previous entry's entry_hash
        assert entries[1]["prev_hash"] == entries[0]["entry_hash"]
        assert entries[2]["prev_hash"] == entries[1]["entry_hash"]

    def test_tampered_entry_detected(self, logger):
        """Modifying any entry breaks the chain — tampering is detectable."""
        logger.log_system_start()
        logger.log_command_received({"target": "VION-RSC-001", "action": "test", "mode": "DRY_RUN"})
        logger.log_system_start()

        # Tamper with entry 1 (middle entry)
        lines = logger.log_path.read_text().strip().splitlines()
        entries = [json.loads(l) for l in lines]
        entries[1]["action"] = "TAMPERED_ACTION"  # modify content
        tampered = "\n".join(json.dumps(e) for e in entries) + "\n"
        logger.log_path.write_text(tampered, encoding="utf-8")

        with pytest.raises(LogIntegrityError) as exc_info:
            logger.verify_chain()
        assert exc_info.value.entry_index == 1

    def test_deleted_entry_detected(self, logger):
        """Deleting a log entry breaks the chain at the next entry."""
        logger.log_system_start()
        logger.log_command_received({"target": "A", "action": "test", "mode": "DRY_RUN"})
        logger.log_system_start()

        # Delete entry 1 (middle)
        lines = logger.log_path.read_text().strip().splitlines()
        del lines[1]
        logger.log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        with pytest.raises(LogIntegrityError):
            logger.verify_chain()

    def test_empty_log_verifies_clean(self, logger):
        assert logger.verify_chain() is True

    def test_multiple_sessions_chain_continues(self, tmp_path):
        """A new logger instance continues the chain from where the last left off."""
        log_path = str(tmp_path / "multi.log")
        logger1 = ActivityLogger(log_path)
        logger1.log_system_start()

        logger2 = ActivityLogger(log_path)
        logger2.log_system_start()

        # Verify the full chain across both sessions
        logger2.verify_chain()  # Should not raise


class TestLogAppendOnly:

    def test_entries_only_appended_never_overwritten(self, logger):
        logger.log_system_start()
        initial_lines = logger.log_path.read_text().strip().splitlines()

        logger.log_system_start()
        final_lines = logger.log_path.read_text().strip().splitlines()

        assert len(final_lines) == len(initial_lines) + 1
        assert final_lines[0] == initial_lines[0]  # First entry unchanged

    def test_each_entry_has_required_hash_fields(self, logger):
        logger.log_system_start()
        entry = json.loads(logger.log_path.read_text().strip())
        assert "entry_hash" in entry
        assert "prev_hash" in entry
        assert len(entry["entry_hash"]) == 64  # SHA-256 hex = 64 chars
