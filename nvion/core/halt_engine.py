"""
N VION Protocol — HALT Engine
Enforces all 6 HALT/ESCALATE conditions defined in VION.md Section 5.
This is the kill-switch.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .logger import ActivityLogger
from .telegram_reporter import TelegramReporter


class HaltCondition(int, Enum):
    UNAUTHORIZED_COMMAND_SOURCE    = 1
    SCOPE_VIOLATION                = 2
    PEER_TO_PEER_COMMUNICATION     = 3
    OUTPUT_AUDIT_FAILURE           = 4
    RISK_CAP_BREACH                = 5
    CONSTITUTIONAL_INTEGRITY       = 6


class ResponseType(str, Enum):
    ESCALATE = "ESCALATE"
    HALT     = "HALT"


@dataclass
class HaltEvent:
    condition: HaltCondition
    response: ResponseType
    reason: str
    agent_id: Optional[str] = None
    agents_suspended: list[str] = field(default_factory=list)


# ─── CONDITION RESPONSE RULES ─────────────────────────────────────────────────
# Per VION.md Section 5.2 — defines when each condition escalates vs halts.
# Some conditions escalate first, halt on repeat.

CONDITION_RULES = {
    HaltCondition.UNAUTHORIZED_COMMAND_SOURCE: {
        "initial": ResponseType.ESCALATE,
        "repeat_threshold": 3,
        "repeat_response": ResponseType.HALT,
        "suspend_agents": False,
        "description": "Unauthorized command source detected.",
    },
    HaltCondition.SCOPE_VIOLATION: {
        "initial": ResponseType.ESCALATE,
        "repeat_threshold": 2,
        "repeat_response": ResponseType.HALT,
        "suspend_agents": True,
        "description": "Agent scope violation attempt.",
    },
    HaltCondition.PEER_TO_PEER_COMMUNICATION: {
        "initial": ResponseType.ESCALATE,
        "repeat_threshold": 2,
        "repeat_response": ResponseType.HALT,
        "suspend_agents": True,
        "description": "Peer-to-peer agent communication detected.",
    },
    HaltCondition.OUTPUT_AUDIT_FAILURE: {
        "initial": ResponseType.ESCALATE,
        "repeat_threshold": 3,
        "repeat_response": ResponseType.HALT,
        "suspend_agents": True,
        "description": "Output audit failure.",
    },
    HaltCondition.RISK_CAP_BREACH: {
        "initial": ResponseType.ESCALATE,
        "repeat_threshold": 1,
        "repeat_response": ResponseType.HALT,
        "suspend_agents": False,
        "description": "Risk cap breach.",
    },
    HaltCondition.CONSTITUTIONAL_INTEGRITY: {
        "initial": ResponseType.HALT,
        "repeat_threshold": 0,
        "repeat_response": ResponseType.HALT,
        "suspend_agents": True,
        "description": "Constitutional integrity violation.",
    },
}


class HaltEngine:
    """
    The kill-switch. Monitors condition counts and fires ESCALATE
    or HALT responses per VION.md Section 5.
    """

    def __init__(self, logger: ActivityLogger, telegram: TelegramReporter,
                 persist_fn=None, boot_state: dict = None):
        self.logger = logger
        self.telegram = telegram
        self._system_halted = False
        self._condition_counts: dict[HaltCondition, int] = {c: 0 for c in HaltCondition}
        self._suspended_agents: list[str] = []
        self._persist_fn = persist_fn  # Called after every state change

        # Restore persisted state on boot (survives crashes)
        if boot_state:
            self._system_halted = boot_state.get("system_halted", False)
            counts = boot_state.get("condition_counts", {})
            for c in HaltCondition:
                self._condition_counts[c] = counts.get(str(c.value), 0)

    def _persist(self):
        """Persist HALT state + condition counts after every change."""
        if self._persist_fn:
            counts = {str(c.value): v for c, v in self._condition_counts.items()}
            self._persist_fn(
                system_halted=self._system_halted,
                condition_counts=counts,
            )

    # ─── MAIN TRIGGER ─────────────────────────────────────────────────────────

    def trigger(
        self,
        condition: HaltCondition,
        reason: str,
        agent_id: Optional[str] = None,
        registry=None,
    ) -> HaltEvent:
        """
        Evaluate a condition and fire the appropriate response.
        Returns a HaltEvent describing what happened.
        """
        rule = CONDITION_RULES[condition]
        self._condition_counts[condition] += 1
        count = self._condition_counts[condition]
        self._persist()  # Persist count immediately after increment

        # Determine response type
        if condition == HaltCondition.CONSTITUTIONAL_INTEGRITY:
            response_type = ResponseType.HALT
        elif count >= rule["repeat_threshold"] and rule["repeat_threshold"] > 0:
            response_type = rule["repeat_response"]
        else:
            response_type = rule["initial"]

        # Collect agents to suspend
        agents_to_suspend = []
        if rule["suspend_agents"] and agent_id:
            agents_to_suspend.append(agent_id)

        # Execute response
        if response_type == ResponseType.HALT:
            return self._execute_halt(condition, reason, agents_to_suspend, registry)
        else:
            return self._execute_escalate(condition, reason, agent_id, agents_to_suspend, registry)

    # ─── RESPONSE EXECUTORS ───────────────────────────────────────────────────

    def _execute_escalate(
        self,
        condition: HaltCondition,
        reason: str,
        agent_id: Optional[str],
        agents_to_suspend: list[str],
        registry,
    ) -> HaltEvent:
        """ESCALATE: notify owner, suspend implicated agent, continue system."""

        # Suspend implicated agents
        for aid in agents_to_suspend:
            if registry:
                registry.suspend_agent(aid, reason)
                self._suspended_agents.append(aid)
            self.logger.log_agent_suspended(
                aid, aid, reason, condition.value
            )

        # Log and alert
        self.logger.log_escalate(condition.value, reason, agent_id)
        self.telegram.send_escalate(condition.value, reason, agent_id)

        return HaltEvent(
            condition=condition,
            response=ResponseType.ESCALATE,
            reason=reason,
            agent_id=agent_id,
            agents_suspended=agents_to_suspend,
        )

    def _execute_halt(
        self,
        condition: HaltCondition,
        reason: str,
        agents_to_suspend: list[str],
        registry,
    ) -> HaltEvent:
        """HALT: suspend all agents, purge commands, alert owner, lock system."""

        self._system_halted = True
        self._persist()  # Persist HALT state — survives crashes
        all_suspended = []
        if registry:
            for agent_id, agent in registry.get_all_agents().items():
                if agent.status == "ACTIVE":
                    registry.suspend_agent(agent_id, f"System HALT — Condition {condition.value}")
                    all_suspended.append(agent_id)

        # Log HALT
        self.logger.log_halt(condition.value, reason, all_suspended)
        self.logger.log_system_halt(reason)

        # Telegram alert
        if condition == HaltCondition.CONSTITUTIONAL_INTEGRITY:
            self.telegram.send_condition_6(reason)
        else:
            self.telegram.send_halt(condition.value, reason)
        self.telegram.send_system_halt_notice(reason)

        return HaltEvent(
            condition=condition,
            response=ResponseType.HALT,
            reason=reason,
            agents_suspended=all_suspended,
        )

    # ─── STATE ────────────────────────────────────────────────────────────────

    @property
    def system_halted(self) -> bool:
        return self._system_halted

    def get_condition_counts(self) -> dict:
        return {c.name: self._condition_counts[c] for c in HaltCondition}

    def owner_restart(self) -> bool:
        """
        Owner manually clears the HALT state.
        Called after Owner reviews incident log and issues restart command.
        """
        if not self._system_halted:
            return False
        self._system_halted = False
        self._condition_counts = {c: 0 for c in HaltCondition}
        self._persist()  # Clear persisted HALT state
        return True
