"""
N VION Protocol
===============
Universal agent constitution engine.

Drop constitutional governance into any agentic system in minutes.

Quick start:
    from nvion import NSoul

    soul = NSoul()
    result = soul.dispatch(auth_token, target, action)

Full docs: https://nvionprotocol.dev
"""

from datetime import datetime, timezone

from .adapters import (
    AgentRunResult,
    BaseAgentAdapter,
    CrewAIAdapter,
    CustomAgentAdapter,
    FunctionAdapter,
    LangChainAdapter,
    OpenAIAdapter,
)
from .core.auditor import AuditResult, AuditVerdict, BlockReason, NAuditor
from .core.constitution import ConstitutionValidator
from .core.exceptions import (
    AgentNotFoundError,
    AgentSuspendedError,
    AuthTokenExpiredError,
    AuthTokenInvalidError,
    AuthTokenMissingError,
    ConfigMissingError,
    ConstitutionIntegrityError,
    LogIntegrityError,
    NSoulError,
    ScopeViolationError,
    SystemHaltedError,
)
from .core.halt_engine import HaltCondition, HaltEvent, ResponseType
from .core.identity import AgentIdentity, IdentityRegistry
from .core.logger import ActivityLogger, EventType
from .core.orchestrator import Orchestrator, OwnerCommand
from .core.peer_detector import PeerToPeerDetector, PeerViolation
from .core.risk_caps import CapViolation, RiskCapEvaluator
from .core.telegram_reporter import TelegramReporter

__version__ = "1.0.0"
__author__ = "Nathan Daniel / N Nexus"


class NSoul:
    """
    N VION Protocol — Main integration class.

    The single entry point for governing any agent system.

    Usage:
        soul = NSoul()
        result = soul.dispatch(auth_token, "VION-RSC-001", "search papers", "LIVE")
        if result["success"]:
            print("Dispatched")
    """

    def __init__(self):
        self._orchestrator = Orchestrator()

    def dispatch(
        self,
        auth_token: str,
        target: str,
        action: str,
        mode: str = "DRY_RUN",
        explicit_override: bool = False,
    ) -> dict:
        """
        Dispatch a governed command to a registered agent.

        Parameters:
            auth_token        — Owner AUTH token (from VION_AUTH_TOKEN in .env)
            target            — Agent ID to dispatch to (e.g. "VION-RSC-001")
            action            — The task for the agent to perform
            mode              — "DRY_RUN" (validate only) or "LIVE" (execute)
            explicit_override — Set True for agents with DRY_RUN: OVERRIDE_REQUIRED

        Returns:
            dict with keys: success, message, dry_run
        """
        command = OwnerCommand(
            auth_token=auth_token,
            target=target,
            action=action,
            mode=mode,
            explicit_override=explicit_override,
        )
        result = self._orchestrator.process_command(command)
        return {
            "success": result.success,
            "message": result.message,
            "dry_run": result.dry_run,
        }

    def status(self) -> dict:
        """Return current system status."""
        return self._orchestrator.get_status()

    def restart(self, auth_token: str) -> dict:
        """Clear a HALT state. Owner only."""
        return self._orchestrator.restart_after_halt(auth_token)

    def is_halted(self) -> bool:
        """Check if the system is currently halted."""
        return self._orchestrator.halt_engine.system_halted

    @property
    def version(self) -> str:
        return __version__
