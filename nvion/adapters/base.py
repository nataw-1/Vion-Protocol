"""
N VION Protocol — Base Agent Adapter
The bridge between N-VION governance and any external agentic system.

This is the file you extend for each agent framework you want to govern.
One adapter per agent system. The governance layer never changes.

Usage pattern:
    1. Extend BaseAgentAdapter
    2. Implement the _run_agent() method for your specific framework
    3. Call adapter.run() instead of calling your agent directly
    N-VION handles everything else.
"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from ..core.auditor import NAuditor
from ..core.logger import ActivityLogger
from ..core.orchestrator import Orchestrator, OwnerCommand


@dataclass
class AgentRunResult:
    """
    The result of a governed agent run.
    Always check .approved and .success before using .output.
    """
    approved: bool           # Did N-VION approve the command?
    success: bool            # Did the agent run successfully?
    output: Any              # The agent's output (None if blocked or failed)
    agent_id: str            # Which agent ran
    action: str              # What it was asked to do
    mode: str                # DRY_RUN or LIVE
    message: str             # Human readable status message
    dry_run: bool = False    # Was this a dry run?
    blocked_reason: str = "" # Why it was blocked (if approved=False)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def ran(self) -> bool:
        """True if the agent actually executed (approved + success)."""
        return self.approved and self.success


class BaseAgentAdapter(ABC):
    """
    Abstract base adapter. Extend this for any agent framework.

    What this does:
    - Takes a task request
    - Passes it through N-VION governance first
    - If approved, calls your agent via _run_agent()
    - Returns a clean AgentRunResult

    What you implement:
    - _run_agent(action, **kwargs) — call your specific agent here

    Example:

        class MyLangChainAdapter(BaseAgentAdapter):
            def __init__(self, agent):
                super().__init__(agent_id="VION-RSC-001")
                self.agent = agent

            def _run_agent(self, action: str, **kwargs):
                return self.agent.run(action)

        adapter = MyLangChainAdapter(my_langchain_agent)
        result = adapter.run(auth_token, "search AI papers", mode="LIVE")
    """

    def __init__(self, agent_id: str, orchestrator: Optional[Orchestrator] = None):
        """
        Parameters:
            agent_id     — The SOUL agent ID this adapter represents
                           Must match a registration in IDENTITY.md
            orchestrator — Optional: pass an existing Orchestrator instance
                           If not passed, a new one is created from .env config
        """
        self.agent_id = agent_id
        self._orchestrator = orchestrator or Orchestrator()
        self._auditor = NAuditor()  # N Auditor — gates all outputs post-execution

    # ─── PUBLIC API ───────────────────────────────────────────────────────────

    def run(
        self,
        auth_token: str,
        action: str,
        mode: str = "DRY_RUN",
        **kwargs,
    ) -> AgentRunResult:
        """
        The main entry point. Call this instead of calling your agent directly.

        Parameters:
            auth_token — Owner AUTH token (from VION_AUTH_TOKEN env var)
            action     — What you want the agent to do (plain English)
            mode       — "DRY_RUN" (default, safe) or "LIVE" (executes)
            **kwargs   — Any extra arguments passed to your _run_agent()

        Returns:
            AgentRunResult with approved, success, output, message fields
        """

        # ── Step 1: Pass through N-VION governance ─────────────────────────
        command = OwnerCommand(
            auth_token=auth_token,
            target=self.agent_id,
            action=action,
            mode=mode,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        dispatch = self._orchestrator.process_command(command)

        # ── Step 2: If governance blocks it, stop here ──────────────────────
        if not dispatch.success:
            return AgentRunResult(
                approved=False,
                success=False,
                output=None,
                agent_id=self.agent_id,
                action=action,
                mode=mode,
                message=dispatch.message,
                blocked_reason=dispatch.message,
            )

        # ── Step 3: If dry run, return without executing ────────────────────
        if dispatch.dry_run:
            return AgentRunResult(
                approved=True,
                success=True,
                output=None,
                agent_id=self.agent_id,
                action=action,
                mode="DRY_RUN",
                dry_run=True,
                message=(
                    f"[DRY RUN] Command approved and validated.\n"
                    f"Agent {self.agent_id} is authorized for: {action}\n"
                    f"Re-run with mode='LIVE' to execute."
                ),
            )

        # ── Step 4: Governance approved — run the actual agent ──────────────
        try:
            output = self._run_agent(action, **kwargs)
        except Exception as e:
            return AgentRunResult(
                approved=True,
                success=False,
                output=None,
                agent_id=self.agent_id,
                action=action,
                mode="LIVE",
                message=f"Agent {self.agent_id} failed during execution: {str(e)}",
                blocked_reason=str(e),
            )

        # ── Step 5: N Auditor gates output before it leaves the system ──────
        # Per VION.md Section 2.4 — all outputs gated before delivery.
        # AUDIT_REQUIRED: YES is set on every registered agent.
        agent_identity = self._orchestrator.registry.get_agent(self.agent_id)
        audit_result = self._auditor.audit(
            agent_id=self.agent_id,
            action=action,
            output=output,
            agent=agent_identity,
        )

        if audit_result.blocked:
            from ..core.halt_engine import HaltCondition
            self._orchestrator.halt_engine.trigger(
                HaltCondition.OUTPUT_AUDIT_FAILURE,
                f"N Auditor blocked output from {self.agent_id}: {audit_result.reason}",
                agent_id=self.agent_id,
                registry=self._orchestrator.registry,
            )
            self._orchestrator.logger.log_audit_block(
                self.agent_id, action, audit_result.reason
            )
            return AgentRunResult(
                approved=True,
                success=False,
                output=None,
                agent_id=self.agent_id,
                action=action,
                mode="LIVE",
                message=f"N Auditor blocked output — {audit_result.reason}",
                blocked_reason=(
                    audit_result.block_reason.value
                    if audit_result.block_reason else "AUDIT_FAILURE"
                ),
            )

        # Output passed audit — log and deliver
        self._orchestrator.logger.log_audit_pass(self.agent_id, action)
        return AgentRunResult(
            approved=True,
            success=True,
            output=output,
            agent_id=self.agent_id,
            action=action,
            mode="LIVE",
            message=f"Agent {self.agent_id} completed: {action}. Output audited and approved.",
        )

    # ─── IMPLEMENT THIS ───────────────────────────────────────────────────────

    @abstractmethod
    def _run_agent(self, action: str, **kwargs) -> Any:
        """
        Implement this method for your specific agent framework.

        This is the ONLY method you write. Everything else is handled by
        N VION Protocol.

        Parameters:
            action  — The task string approved by N-VION
            **kwargs — Any extra args you passed to run()

        Returns:
            Whatever your agent returns (string, dict, list, any type)

        Examples:

            # LangChain
            def _run_agent(self, action, **kwargs):
                return self.agent.run(action)

            # CrewAI
            def _run_agent(self, action, **kwargs):
                return self.crew.kickoff(inputs={"task": action})

            # OpenAI
            def _run_agent(self, action, **kwargs):
                response = self.client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": action}]
                )
                return response.choices[0].message.content

            # Hermes / OpenClaw / Custom
            def _run_agent(self, action, **kwargs):
                return self.agent.execute(prompt=action)
        """
        raise NotImplementedError

    # ─── UTILITIES ────────────────────────────────────────────────────────────

    def is_system_halted(self) -> bool:
        """Check if N-VION has halted the system."""
        return self._orchestrator.halt_engine.system_halted

    def get_status(self) -> dict:
        """Get full N-VION system status."""
        return self._orchestrator.get_status()
