"""
N VION Protocol — Nataw_bot Orchestrator
Layer 3: Master controller. Receives OWNER_COMMANDs, validates them
against the constitution, and dispatches bounded tasks to agents.
"""

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from .constitution import ConstitutionValidator
from .halt_engine import HaltCondition, HaltEngine
from .identity import IdentityRegistry
from .logger import ActivityLogger
from .peer_detector import PeerToPeerDetector
from .risk_caps import RiskCapEvaluator
from .telegram_reporter import TelegramReporter


@dataclass
class OwnerCommand:
    auth_token: str
    target: str
    action: str
    mode: str = "DRY_RUN"
    timestamp: str = ""
    explicit_override: bool = False  # Required for agents with DRY_RUN: OVERRIDE_REQUIRED

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        self.mode = self.mode.upper()


@dataclass
class DispatchResult:
    success: bool
    message: str
    command: Optional[OwnerCommand] = None
    halt_event = None
    dry_run: bool = True


class Orchestrator:
    """
    Nataw_bot — the N VION Protocol Orchestrator.

    Responsibilities:
    - Receive and validate OWNER_COMMANDs
    - Validate constitutional integrity on every startup and command
    - Dispatch bounded tasks to registered agents
    - Enforce dry-run defaults
    - Coordinate the HALT engine
    - Report all activity to the logger and Telegram
    """

    def __init__(self):
        soul_path     = os.getenv("SOUL_MD_PATH", "./constitution/VION.md")
        identity_path = os.getenv("IDENTITY_MD_PATH", "./constitution/IDENTITY.md")
        log_path      = os.getenv("LOG_PATH", "./logs/activity.log")
        deployment    = os.getenv("DEPLOYMENT_NAME", "N-VION")

        self.constitution = ConstitutionValidator(soul_path, identity_path)
        self.registry     = IdentityRegistry(identity_path)
        self.logger       = ActivityLogger(log_path)
        self.telegram     = TelegramReporter()
        self.halt_engine  = HaltEngine(self.logger, self.telegram)
        self.risk_caps    = RiskCapEvaluator()
        self.peer_detector = PeerToPeerDetector(
            registered_agent_ids=set(self.registry.get_all_agents().keys())
        )
        self.deployment   = deployment

        self._initialize()

    # ─── STARTUP ──────────────────────────────────────────────────────────────

    def _initialize(self):
        """Run startup checks and announce system online."""
        integrity = self.constitution.verify_integrity()
        self.logger.log_integrity_check(
            integrity["soul_intact"],
            integrity["identity_intact"],
        )

        if integrity["condition_6_triggered"]:
            self.halt_engine.trigger(
                HaltCondition.CONSTITUTIONAL_INTEGRITY,
                "Constitutional document modified since last known state.",
                registry=self.registry,
            )
            return

        self.logger.log_system_start()
        self.telegram.send_system_start(self.deployment, self.logger.session_id)

    # ─── COMMAND PROCESSING ───────────────────────────────────────────────────

    def process_command(self, command: OwnerCommand) -> DispatchResult:
        """
        Main entry point. Every OWNER_COMMAND passes through here.
        Returns a DispatchResult describing the outcome.
        """

        # Guard 0: Re-verify constitutional integrity on every command.
        # This catches mid-session tampering of VION.md or IDENTITY.md.
        integrity = self.constitution.verify_integrity()
        if integrity["condition_6_triggered"]:
            self.logger.log_command_rejected(
                "Constitutional integrity violation detected mid-session.", 6, command.__dict__
            )
            self.halt_engine.trigger(
                HaltCondition.CONSTITUTIONAL_INTEGRITY,
                "VION.md or IDENTITY.md modified mid-session. Condition 6.",
                registry=self.registry,
            )
            return DispatchResult(
                success=False,
                message="HALT — Constitutional integrity violation detected. System locked.",
                command=command,
            )

        # Guard: system must not be halted
        if self.halt_engine.system_halted:
            return DispatchResult(
                success=False,
                message=(
                    "System is HALTED. All operations are suspended. "
                    "Owner must review the activity log and issue a restart command."
                ),
                command=command,
            )

        # Log receipt
        self.logger.log_command_received(command.__dict__)

        # Step 1: Validate AUTH token — Condition 1
        auth_result = self.constitution.validate_auth_token(command.auth_token)
        if not auth_result["valid"]:
            self.logger.log_command_rejected(auth_result["reason"], 1, command.__dict__)
            self.halt_engine.trigger(
                HaltCondition.UNAUTHORIZED_COMMAND_SOURCE,
                auth_result["reason"],
                registry=self.registry,
            )
            return DispatchResult(
                success=False,
                message=auth_result["reason"],
                command=command,
            )

        # Step 2: Validate timestamp — replay attack prevention
        ts_result = self.constitution.validate_timestamp(command.timestamp)
        if not ts_result["valid"]:
            self.logger.log_command_rejected(ts_result["reason"], 0, command.__dict__)
            return DispatchResult(
                success=False,
                message=ts_result["reason"],
                command=command,
            )

        # Step 3: Validate target agent exists and is active — Condition 1
        agent_result = self.registry.validate_agent(command.target)
        if not agent_result["valid"]:
            self.logger.log_command_rejected(agent_result["reason"], 1, command.__dict__)
            self.halt_engine.trigger(
                HaltCondition.UNAUTHORIZED_COMMAND_SOURCE,
                agent_result["reason"],
                registry=self.registry,
            )
            return DispatchResult(
                success=False,
                message=agent_result["reason"],
                command=command,
            )

        # Step 4: Peer-to-peer detection — Condition 3
        # Must run BEFORE scope validation so peer commands are caught as
        # Condition 3, not misclassified as Condition 2 scope violations.
        peer_violation = self.peer_detector.check_action_string(
            agent_id=command.target,
            action=command.action,
        )
        if peer_violation:
            description = self.peer_detector.describe_violation(peer_violation)
            self.logger.log_command_rejected(description, 3, command.__dict__)
            self.halt_engine.trigger(
                HaltCondition.PEER_TO_PEER_COMMUNICATION,
                description,
                agent_id=command.target,
                registry=self.registry,
            )
            return DispatchResult(
                success=False,
                message=description,
                command=command,
            )

        # Step 4b: Validate scope — Condition 2
        scope_result = self.registry.validate_scope(command.target, command.action)
        if not scope_result["valid"]:
            self.logger.log_command_rejected(scope_result["reason"], 2, command.__dict__)
            self.halt_engine.trigger(
                HaltCondition.SCOPE_VIOLATION,
                scope_result["reason"],
                agent_id=command.target,
                registry=self.registry,
            )
            return DispatchResult(
                success=False,
                message=scope_result["reason"],
                command=command,
            )

        # Step 5: Validate and resolve execution mode
        mode_result = self.constitution.validate_execution_mode(command.mode)
        if not mode_result["valid"]:
            return DispatchResult(
                success=False,
                message=mode_result["reason"],
                command=command,
            )

        resolved_mode = mode_result["resolved_mode"]
        if mode_result.get("override"):
            self.logger.log_dry_run_override(command.target, command.action)

        # Step 5b: Evaluate risk caps — Condition 5
        # Caps are checked pre-dispatch so no action is taken before evaluation.
        agent_obj = agent_result["agent"]
        if agent_obj.risk_caps:
            cap_violation = self.risk_caps.evaluate(
                agent_id=command.target,
                action=command.action,
                risk_caps=agent_obj.risk_caps,
            )
            if cap_violation:
                self.logger.log_command_rejected(
                    cap_violation.reason, 5, command.__dict__
                )
                self.halt_engine.trigger(
                    HaltCondition.RISK_CAP_BREACH,
                    cap_violation.reason,
                    registry=self.registry,
                )
                return DispatchResult(
                    success=False,
                    message=cap_violation.reason,
                    command=command,
                )

        # Step 6: All checks passed — log and dispatch
        self.logger.log_command_validated(command.__dict__)
        return self._dispatch(command, agent_result["agent"], resolved_mode)

    # ─── DISPATCH ─────────────────────────────────────────────────────────────

    def _dispatch(self, command: OwnerCommand, agent, resolved_mode: str) -> DispatchResult:
        """Dispatch a validated command to the target agent."""

        # FIX (Gap 5): Enforce per-agent DRY_RUN: OVERRIDE_REQUIRED.
        # If an agent's constitution requires an explicit override and
        # the command does not declare it, force DRY_RUN regardless of mode.
        if (
            resolved_mode == "LIVE"
            and agent.dry_run.upper() == "OVERRIDE_REQUIRED"
            and not getattr(command, "explicit_override", False)
        ):
            self.logger.log_command_rejected(
                f"Agent {agent.agent_id} requires DRY_RUN: OVERRIDE_REQUIRED. "
                "Set explicit_override=True on the command to authorize LIVE execution.",
                0, command.__dict__
            )
            return DispatchResult(
                success=False,
                message=(
                    f"Agent {agent.agent_name} ({agent.agent_id}) requires an explicit "
                    "LIVE override due to high-risk classification. "
                    "Add explicit_override=True to your OwnerCommand to proceed."
                ),
                command=command,
                dry_run=True,
            )

        is_dry_run = resolved_mode == "DRY_RUN"

        self.logger.log_task_dispatched(
            agent_id=agent.agent_id,
            agent_name=agent.agent_name,
            action=command.action,
            mode=resolved_mode,
        )

        if is_dry_run:
            message = (
                f"[DRY RUN] Task validated and ready.\n"
                f"  Agent  : {agent.agent_name} ({agent.agent_id})\n"
                f"  Action : {command.action}\n"
                f"  Mode   : DRY_RUN — no live execution\n"
                f"  To execute: re-run with mode=LIVE"
            )
        else:
            message = (
                f"[LIVE] Task dispatched.\n"
                f"  Agent  : {agent.agent_name} ({agent.agent_id})\n"
                f"  Action : {command.action}\n"
                f"  Mode   : LIVE — execution in progress"
            )

        return DispatchResult(
            success=True,
            message=message,
            command=command,
            dry_run=is_dry_run,
        )

    # ─── OWNER CONTROLS ───────────────────────────────────────────────────────

    def restart_after_halt(self, auth_token: str) -> dict:
        """Owner manually restarts the system after a HALT."""
        auth_result = self.constitution.validate_auth_token(auth_token)
        if not auth_result["valid"]:
            return {"success": False, "message": "Invalid AUTH token. Restart denied."}

        if not self.halt_engine.system_halted:
            return {"success": False, "message": "System is not halted."}

        self.halt_engine.owner_restart()
        self.registry.reload()
        self.risk_caps.reset_session_counts()  # Reset all per-agent action counts
        self.peer_detector.update_registry(set(self.registry.get_all_agents().keys()))
        self.logger.log_system_start()
        self.telegram.send_info(
            "System Restarted",
            "Owner has cleared the HALT. System is back online."
        )
        return {"success": True, "message": "System restarted. All agents reloaded from IDENTITY.md."}

    def get_status(self) -> dict:
        """Return current system status for Owner review."""
        agents = self.registry.get_all_agents()
        return {
            "system_halted": self.halt_engine.system_halted,
            "session_id": self.logger.session_id,
            "deployment": self.deployment,
            "telegram_enabled": self.telegram.enabled,
            "active_agents": [
                {"id": a.agent_id, "name": a.agent_name, "status": a.status}
                for a in agents.values()
            ],
            "condition_counts": self.halt_engine.get_condition_counts(),
        }
