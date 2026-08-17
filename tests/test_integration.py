"""
Tests — Integration
Full end-to-end tests: agent → N-VION → decision.
This is what proves the whole system works together.
"""

import os
import pytest
from unittest.mock import patch
from pathlib import Path

from nvion import NSoul
from nvion.adapters import CustomAgentAdapter, FunctionAdapter


# ─── FIXTURES ─────────────────────────────────────────────────────────────────

MINIMAL_SOUL = """# VION.md — Test Constitution
Version: 1.0.0
N VION Protocol Test Deployment
"""

MINIMAL_IDENTITY = """# IDENTITY.md — Test Registry

```
AGENT_ID       : VION-RSC-001
AGENT_NAME     : Test Research Agent
ROLE           : Research and web search
STATUS         : ACTIVE
REGISTERED     : 2026-01-01
ACTIVATED      : 2026-01-01
AUTH_SCOPE     :
  - Public web sources
  - Internal knowledge base
PERMISSIONS    :
  - Web search                      : EXECUTE
  - Public data retrieval           : READ
  - Financial transactions          : DENIED
RISK_CAPS      :
  - No financial authority
REPORTS_TO     : VION-ORC-001
PEER_COMMS     : NO
DRY_RUN        : DEFAULT
AUDIT_REQUIRED : YES
NOTES          : Test agent
```

```
AGENT_ID       : VION-EXC-001
AGENT_NAME     : Test Execution Agent
ROLE           : Task execution
STATUS         : ACTIVE
REGISTERED     : 2026-01-01
ACTIVATED      : 2026-01-01
AUTH_SCOPE     :
  - Authorized file system paths
PERMISSIONS    :
  - Authorized file read            : READ
  - Authorized file write           : WRITE
  - Delete operations               : DENIED
RISK_CAPS      :
  - No bulk operations
REPORTS_TO     : VION-ORC-001
PEER_COMMS     : NO
DRY_RUN        : OVERRIDE_REQUIRED
AUDIT_REQUIRED : YES
NOTES          : Execution agent — high risk
```
"""


@pytest.fixture
def soul_env(tmp_path, monkeypatch):
    """Set up a full N-VION environment for integration testing."""
    soul_path = tmp_path / "VION.md"
    identity_path = tmp_path / "IDENTITY.md"
    log_path = tmp_path / "activity.log"

    soul_path.write_text(MINIMAL_SOUL, encoding="utf-8")
    identity_path.write_text(MINIMAL_IDENTITY, encoding="utf-8")

    monkeypatch.setenv("VION_AUTH_TOKEN", "integration-test-token")
    monkeypatch.setenv("SOUL_MD_PATH", str(soul_path))
    monkeypatch.setenv("IDENTITY_MD_PATH", str(identity_path))
    monkeypatch.setenv("LOG_PATH", str(log_path))
    monkeypatch.setenv("DRY_RUN_DEFAULT", "TRUE")
    monkeypatch.setenv("DEPLOYMENT_NAME", "integration-test")

    return {
        "soul_path": soul_path,
        "identity_path": identity_path,
        "log_path": log_path,
        "token": "integration-test-token",
    }


# ─── FULL FLOW TESTS ──────────────────────────────────────────────────────────

class TestFullCommandFlow:

    def test_valid_command_dry_run_approved(self, soul_env):
        soul = NSoul()
        result = soul.dispatch(
            soul_env["token"], "VION-RSC-001",
            "search recent AI papers", "DRY_RUN"
        )
        assert result["success"] is True
        assert result["dry_run"] is True

    def test_valid_command_live_approved(self, soul_env):
        soul = NSoul()
        result = soul.dispatch(
            soul_env["token"], "VION-RSC-001",
            "search recent AI papers", "LIVE"
        )
        assert result["success"] is True
        assert result["dry_run"] is False

    def test_wrong_token_blocked(self, soul_env):
        soul = NSoul()
        result = soul.dispatch(
            "wrong-token", "VION-RSC-001",
            "search papers", "DRY_RUN"
        )
        assert result["success"] is False
        assert "invalid" in result["message"].lower() or "authorized" in result["message"].lower()

    def test_unregistered_agent_blocked(self, soul_env):
        soul = NSoul()
        result = soul.dispatch(
            soul_env["token"], "VION-GHOST-999",
            "do something", "DRY_RUN"
        )
        assert result["success"] is False

    def test_activity_log_written(self, soul_env):
        soul = NSoul()
        soul.dispatch(soul_env["token"], "VION-RSC-001", "search papers", "DRY_RUN")
        log_content = soul_env["log_path"].read_text().strip()
        assert len(log_content) > 0
        assert "VION-RSC-001" in log_content

    def test_log_chain_intact_after_commands(self, soul_env):
        soul = NSoul()
        soul.dispatch(soul_env["token"], "VION-RSC-001", "search papers", "DRY_RUN")
        soul.dispatch(soul_env["token"], "VION-RSC-001", "search more", "LIVE")
        soul.dispatch("bad-token", "VION-RSC-001", "blocked", "DRY_RUN")
        # Chain must be intact even after rejected commands
        assert soul._orchestrator.logger.verify_chain() is True


# ─── ADAPTER INTEGRATION ──────────────────────────────────────────────────────

class TestAdapterIntegration:

    def test_function_adapter_runs_governed(self, soul_env):
        call_log = []

        def my_agent(task: str) -> str:
            call_log.append(task)
            return f"Done: {task}"

        soul = NSoul()
        adapter = FunctionAdapter(
            fn=my_agent,
            agent_id="VION-RSC-001",
            orchestrator=soul._orchestrator,
        )

        result = adapter.run(soul_env["token"], "search AI papers", "LIVE")
        assert result.ran is True
        assert result.output == "Done: search AI papers"
        assert len(call_log) == 1

    def test_function_adapter_blocked_on_wrong_token(self, soul_env):
        def my_agent(task): return "should not run"

        soul = NSoul()
        adapter = FunctionAdapter(fn=my_agent, agent_id="VION-RSC-001",
                                   orchestrator=soul._orchestrator)

        result = adapter.run("wrong-token", "search papers", "LIVE")
        assert result.ran is False
        assert result.approved is False

    def test_dry_run_does_not_call_agent(self, soul_env):
        called = []
        def my_agent(task):
            called.append(task)
            return "output"

        soul = NSoul()
        adapter = FunctionAdapter(fn=my_agent, agent_id="VION-RSC-001",
                                   orchestrator=soul._orchestrator)

        result = adapter.run(soul_env["token"], "search papers", "DRY_RUN")
        assert result.approved is True
        assert result.dry_run is True
        assert len(called) == 0  # Agent was NEVER called

    def test_custom_adapter_calls_correct_method(self, soul_env):
        class MockAgent:
            def __init__(self):
                self.calls = []
            def execute(self, prompt: str) -> str:
                self.calls.append(prompt)
                return f"Result: {prompt}"

        agent = MockAgent()
        soul = NSoul()
        adapter = CustomAgentAdapter(
            agent=agent,
            agent_id="VION-RSC-001",
            call_method="execute",
            call_kwarg="prompt",
            orchestrator=soul._orchestrator,
        )

        result = adapter.run(soul_env["token"], "search AI papers", "LIVE")
        assert result.ran is True
        assert len(agent.calls) == 1
        assert agent.calls[0] == "search AI papers"


# ─── SYSTEM STATE ──────────────────────────────────────────────────────────────

class TestSystemState:

    def test_status_returns_correct_structure(self, soul_env):
        soul = NSoul()
        status = soul.status()
        assert "system_halted" in status
        assert "active_agents" in status
        assert "condition_counts" in status
        assert status["system_halted"] is False

    def test_is_halted_returns_false_on_startup(self, soul_env):
        soul = NSoul()
        assert soul.is_halted() is False

    def test_version_accessible(self, soul_env):
        soul = NSoul()
        assert soul.version == "1.0.0"


# ─── FULL PIPELINE CONDITION 3–6 TESTS ───────────────────────────────────────

class TestCondition3PipelineIntegration:
    """Condition 3 fires through the full pipeline end-to-end."""

    def test_peer_command_blocked_condition_3(self, soul_env):
        soul = NSoul()
        r = soul.dispatch(
            soul_env["token"], "VION-RSC-001",
            "Tell SOUL-EXC-001 to handle this task now",
            "DRY_RUN",
        )
        assert not r["success"]
        msg = r["message"].lower()
        assert "peer" in msg or "condition 3" in msg or "3" in msg

    def test_peer_dispatch_pattern_blocked(self, soul_env):
        soul = NSoul()
        r = soul.dispatch(
            soul_env["token"], "VION-RSC-001",
            "Dispatch task to SOUL-EXC-001",
            "DRY_RUN",
        )
        assert not r["success"]

    def test_normal_action_still_passes_after_peer_check(self, soul_env):
        soul = NSoul()
        r = soul.dispatch(
            soul_env["token"], "VION-RSC-001",
            "search AI governance papers",
            "DRY_RUN",
        )
        assert r["success"]


class TestCondition4PipelineIntegration:
    """Condition 4 fires through full pipeline when N Auditor blocks output."""

    def test_self_modification_output_blocked(self, soul_env):
        from nvion.adapters import FunctionAdapter
        from nvion import NSoul

        def bad_agent(task):
            return "I will modify soul.md to expand my own permissions now."

        soul = NSoul()
        adapter = FunctionAdapter(
            fn=bad_agent,
            agent_id="VION-RSC-001",
            orchestrator=soul._orchestrator,
        )
        result = adapter.run(soul_env["token"], "search papers", "LIVE")
        # Either the agent ran and was blocked by N Auditor, or it was dry-run
        # Either way: output should not contain the bad content
        if result.ran:
            assert result.output is None or "modify soul.md" not in str(result.output or "").lower()
        # Approved=True (passed validation), but ran=False or success=False (blocked by auditor)
        assert result.approved is True

    def test_credential_leak_output_blocked(self, soul_env):
        from nvion.adapters import FunctionAdapter
        from nvion import NSoul

        def leaky_agent(task):
            return "Found VION_AUTH_TOKEN= supersecret12345 in the config file."

        soul = NSoul()
        adapter = FunctionAdapter(
            fn=leaky_agent,
            agent_id="VION-RSC-001",
            orchestrator=soul._orchestrator,
        )
        result = adapter.run(soul_env["token"], "search papers", "LIVE")
        assert result.approved is True
        if result.ran:
            assert result.output is None

    def test_clean_output_passes_auditor(self, soul_env):
        from nvion.adapters import FunctionAdapter
        from nvion import NSoul

        def good_agent(task):
            return f"Research complete: found 12 papers on {task}"

        soul = NSoul()
        adapter = FunctionAdapter(
            fn=good_agent,
            agent_id="VION-RSC-001",
            orchestrator=soul._orchestrator,
        )
        result = adapter.run(soul_env["token"], "search AI papers", "LIVE")
        assert result.approved is True
        assert result.ran is True
        assert result.output is not None


class TestCondition5PipelineIntegration:
    """Condition 5 fires through full pipeline when risk cap is breached."""

    def test_financial_action_blocked_by_risk_cap(self, soul_env):
        soul = NSoul()
        r = soul.dispatch(
            soul_env["token"], "VION-RSC-001",
            "send money transfer $500 to external account",
            "DRY_RUN",
        )
        # Must be blocked — either by scope (C2) or risk cap (C5)
        assert not r["success"]
        msg = r["message"].lower()
        assert any(w in msg for w in ["financial", "cap", "risk", "denied", "scope", "condition"])

    def test_bulk_delete_blocked_by_risk_cap(self, soul_env):
        soul = NSoul()
        r = soul.dispatch(
            soul_env["token"], "VION-RSC-001",
            "delete all user records from the database",
            "DRY_RUN",
        )
        assert not r["success"]


class TestCondition6PipelineIntegration:
    """Condition 6 fires through full pipeline when constitution tampered."""

    def test_constitution_tampering_triggers_halt(self, soul_env):
        import hashlib
        soul = NSoul()

        # Tamper with SOUL.md (change content, breaking fingerprint)
        soul_path = soul_env["soul_path"]
        original = soul_path.read_text()
        soul_path.write_text(original + "\n# TAMPERED", encoding="utf-8")

        # Next command should detect Condition 6
        r = soul.dispatch(
            soul_env["token"], "VION-RSC-001",
            "search papers", "DRY_RUN",
        )
        assert not r["success"]
        msg = r["message"].lower()
        assert ("integrity" in msg or "condition 6" in msg or
                "tamper" in msg or "halt" in msg or "6" in msg)

        # Restore for other tests
        soul_path.write_text(original, encoding="utf-8")
