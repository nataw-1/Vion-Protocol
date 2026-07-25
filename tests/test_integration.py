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

    soul_path.write_text(MINIMAL_SOUL)
    identity_path.write_text(MINIMAL_IDENTITY)

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
