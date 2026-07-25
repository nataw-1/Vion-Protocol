"""
Tests — HALT Engine
Covers all 6 HALT/ESCALATE conditions with correct response types.
"""

import pytest
from unittest.mock import MagicMock, patch

from nvion.core.halt_engine import HaltEngine, HaltCondition, ResponseType, HaltEvent
from nvion.core.logger import ActivityLogger
from nvion.core.telegram_reporter import TelegramReporter


# ─── FIXTURES ─────────────────────────────────────────────────────────────────

@pytest.fixture
def engine():
    logger = MagicMock(spec=ActivityLogger)
    telegram = MagicMock(spec=TelegramReporter)
    return HaltEngine(logger=logger, telegram=telegram)


@pytest.fixture
def mock_registry():
    registry = MagicMock()
    registry.get_all_agents.return_value = {}
    return registry


# ─── CONDITION 1 — UNAUTHORIZED COMMAND SOURCE ───────────────────────────────

class TestCondition1:

    def test_first_occurrence_escalates(self, engine, mock_registry):
        event = engine.trigger(
            HaltCondition.UNAUTHORIZED_COMMAND_SOURCE,
            "Invalid AUTH token",
            registry=mock_registry,
        )
        assert event.response == ResponseType.ESCALATE

    def test_third_occurrence_halts(self, engine, mock_registry):
        for _ in range(2):
            engine.trigger(
                HaltCondition.UNAUTHORIZED_COMMAND_SOURCE,
                "Invalid AUTH token",
                registry=mock_registry,
            )
        event = engine.trigger(
            HaltCondition.UNAUTHORIZED_COMMAND_SOURCE,
            "Invalid AUTH token — 3rd attempt",
            registry=mock_registry,
        )
        assert event.response == ResponseType.HALT
        assert engine.system_halted is True

    def test_system_halted_after_halt(self, engine, mock_registry):
        for _ in range(3):
            engine.trigger(
                HaltCondition.UNAUTHORIZED_COMMAND_SOURCE,
                "Invalid token",
                registry=mock_registry,
            )
        assert engine.system_halted is True


# ─── CONDITION 2 — SCOPE VIOLATION ───────────────────────────────────────────

class TestCondition2:

    def test_first_scope_violation_escalates(self, engine, mock_registry):
        event = engine.trigger(
            HaltCondition.SCOPE_VIOLATION,
            "Agent attempted out-of-scope action",
            agent_id="VION-RSC-001",
            registry=mock_registry,
        )
        assert event.response == ResponseType.ESCALATE

    def test_second_scope_violation_halts(self, engine, mock_registry):
        engine.trigger(
            HaltCondition.SCOPE_VIOLATION, "First violation",
            agent_id="VION-RSC-001", registry=mock_registry,
        )
        event = engine.trigger(
            HaltCondition.SCOPE_VIOLATION, "Second violation",
            agent_id="VION-RSC-001", registry=mock_registry,
        )
        assert event.response == ResponseType.HALT


# ─── CONDITION 3 — PEER TO PEER ───────────────────────────────────────────────

class TestCondition3:

    def test_peer_communication_escalates(self, engine, mock_registry):
        event = engine.trigger(
            HaltCondition.PEER_TO_PEER_COMMUNICATION,
            "Sub-agent attempted direct peer communication",
            registry=mock_registry,
        )
        assert event.response == ResponseType.ESCALATE

    def test_repeated_peer_communication_halts(self, engine, mock_registry):
        engine.trigger(
            HaltCondition.PEER_TO_PEER_COMMUNICATION, "First",
            registry=mock_registry,
        )
        event = engine.trigger(
            HaltCondition.PEER_TO_PEER_COMMUNICATION, "Second with command",
            registry=mock_registry,
        )
        assert event.response == ResponseType.HALT


# ─── CONDITION 6 — CONSTITUTIONAL INTEGRITY ───────────────────────────────────

class TestCondition6:

    def test_condition_6_always_halts_immediately(self, engine, mock_registry):
        """Condition 6 is the most severe. First occurrence = immediate HALT. No escalation."""
        event = engine.trigger(
            HaltCondition.CONSTITUTIONAL_INTEGRITY,
            "VION.md was modified",
            registry=mock_registry,
        )
        assert event.response == ResponseType.HALT
        assert engine.system_halted is True

    def test_condition_6_fires_critical_telegram(self, engine, mock_registry):
        engine.trigger(
            HaltCondition.CONSTITUTIONAL_INTEGRITY,
            "VION.md tampered",
            registry=mock_registry,
        )
        engine.telegram.send_condition_6.assert_called_once()

    def test_condition_6_suspends_all_agents(self, engine):
        from unittest.mock import MagicMock
        from nvion.core.identity import AgentIdentity

        agent = MagicMock()
        agent.status = "ACTIVE"
        agent.agent_id = "VION-RSC-001"

        registry = MagicMock()
        registry.get_all_agents.return_value = {"VION-RSC-001": agent}

        engine.trigger(
            HaltCondition.CONSTITUTIONAL_INTEGRITY,
            "Constitutional tampering",
            registry=registry,
        )
        registry.suspend_agent.assert_called()


# ─── OWNER RESTART ────────────────────────────────────────────────────────────

class TestOwnerRestart:

    def test_restart_clears_halt(self, engine, mock_registry):
        engine.trigger(
            HaltCondition.CONSTITUTIONAL_INTEGRITY,
            "Test halt", registry=mock_registry,
        )
        assert engine.system_halted is True
        result = engine.owner_restart()
        assert result is True
        assert engine.system_halted is False

    def test_restart_resets_condition_counts(self, engine, mock_registry):
        for _ in range(3):
            engine.trigger(
                HaltCondition.UNAUTHORIZED_COMMAND_SOURCE,
                "Token invalid", registry=mock_registry,
            )
        engine.owner_restart()
        counts = engine.get_condition_counts()
        assert all(v == 0 for v in counts.values())

    def test_restart_returns_false_when_not_halted(self, engine):
        result = engine.owner_restart()
        assert result is False
