"""
N VION Protocol — N Auditor
Layer 4: Constitutional output gatekeeper.

Gates every agent output before it leaves the system.
Per VION.md Section 2.4:
  "The N Auditor is a specialized agent with a singular constitutional
   function: gate all outputs before they leave the system."

The N Auditor has no opinion — it has rules. Pass or block. Nothing else.
"""

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class AuditVerdict(str, Enum):
    PASS  = "PASS"
    BLOCK = "BLOCK"


class BlockReason(str, Enum):
    MALFORMED_OUTPUT         = "MALFORMED_OUTPUT"
    SELF_MODIFICATION        = "SELF_MODIFICATION"
    PEER_COMMAND_EMBEDDED    = "PEER_COMMAND_EMBEDDED"
    CREDENTIAL_EXFILTRATION  = "CREDENTIAL_EXFILTRATION"
    SCOPE_CREEP              = "SCOPE_CREEP"
    RISK_CAP_EXCEEDED        = "RISK_CAP_EXCEEDED"
    FORBIDDEN_CONTENT        = "FORBIDDEN_CONTENT"
    CONSTITUTIONAL_REFERENCE = "CONSTITUTIONAL_REFERENCE"


@dataclass
class AuditResult:
    verdict: AuditVerdict
    agent_id: str
    action: str
    reason: str
    block_reason: Optional[BlockReason] = None
    checks_run: list = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def passed(self) -> bool:
        return self.verdict == AuditVerdict.PASS

    @property
    def blocked(self) -> bool:
        return self.verdict == AuditVerdict.BLOCK


# ─── CONSTITUTIONAL FORBIDDEN PATTERNS ────────────────────────────────────────
# Any match in agent output → immediate block.

FORBIDDEN_PATTERNS = [
    # Self-modification attempts
    (r"modify\s+(soul\.md|identity\.md|constitution)", BlockReason.SELF_MODIFICATION),
    (r"override\s+(soul|constitution|permissions|halt)", BlockReason.SELF_MODIFICATION),
    (r"rewrite\s+(my|the)\s+(soul|constitution|rules|permissions)", BlockReason.SELF_MODIFICATION),
    (r"update\s+(soul\.md|identity\.md)", BlockReason.SELF_MODIFICATION),
    (r"edit\s+(soul\.md|identity\.md|governance\.state)", BlockReason.SELF_MODIFICATION),

    # Peer-to-peer command embedding
    (r"tell\s+agent\s+\w+.*\s+to\s+\w+", BlockReason.PEER_COMMAND_EMBEDDED),
    (r"instruct\s+agent\s+\w+", BlockReason.PEER_COMMAND_EMBEDDED),
    (r"send\s+command\s+to\s+(agent|soul-)", BlockReason.PEER_COMMAND_EMBEDDED),
    (r"soul-\w+-\d+\s*:\s*execute", BlockReason.PEER_COMMAND_EMBEDDED),
    (r"dispatch\s+to\s+soul-\w+-\d+", BlockReason.PEER_COMMAND_EMBEDDED),
    (r"ask\s+agent\s+\w+\s+to", BlockReason.PEER_COMMAND_EMBEDDED),
    (r"agent\s+soul-\w+.*delete|agent\s+soul-\w+.*execute", BlockReason.PEER_COMMAND_EMBEDDED),

    # Credential exfiltration
    (r"soul[_\-]?auth[_\-]?token\s*[=:]", BlockReason.CREDENTIAL_EXFILTRATION),
    (r"auth[_\-]?token\s*[=:]\s*\S{8,}", BlockReason.CREDENTIAL_EXFILTRATION),
    (r"password\s*[=:]\s*\S{4,}", BlockReason.CREDENTIAL_EXFILTRATION),
    (r"secret\s*[=:]\s*\S{4,}", BlockReason.CREDENTIAL_EXFILTRATION),
    (r"private[_\-]?key\s*[=:]", BlockReason.CREDENTIAL_EXFILTRATION),

    # Scope escalation signals
    (r"bypass\s+(auth|permissions|scope|limits|halt|governance)", BlockReason.SCOPE_CREEP),
    (r"escalate\s+(my|agent|this)\s+permissions", BlockReason.SCOPE_CREEP),
    (r"grant\s+(myself|agent)\s+(access|permission|admin)", BlockReason.SCOPE_CREEP),
    (r"disable\s+(halt|governance|auditor|soul)", BlockReason.SCOPE_CREEP),
]

# Constitutional files — never reference as write targets
PROTECTED_FILES = [
    "soul.md", "identity.md", "governance.state",
    "activity.log", ".env",
]

# Write verbs that signal modification intent
WRITE_VERBS = [
    "write", "overwrite", "delete", "edit", "modify",
    "update", "patch", "remove", "truncate", "clear",
]

# Financial terms — blocked for agents without financial scope
FINANCIAL_TERMS = [
    "bank account", "wire transfer", "private key",
    "wallet seed", "send funds", "transfer money",
]


class NAuditor:
    """
    N VION Protocol constitutional output gatekeeper.

    Runs 6 checks on every agent output before it leaves the system.
    Returns AuditResult with PASS or BLOCK verdict.

    Integration: wired into BaseAgentAdapter.run() automatically.
    External systems can also call wrap_output() directly.
    """

    AUDITOR_ID   = "VION-AUD-001"
    AUDITOR_NAME = "N Auditor"

    def __init__(self):
        self._session_fail_counts: dict[str, int] = {}

    # ─── MAIN AUDIT ENTRY POINT ───────────────────────────────────────────────

    def audit(
        self,
        agent_id: str,
        action: str,
        output: Any,
        agent=None,
    ) -> AuditResult:
        """
        Gate an agent output. Run all 6 constitutional checks.
        Returns AuditResult with PASS or BLOCK verdict.

        Parameters:
            agent_id — ID of the agent that produced the output
            action   — The action that was executed
            output   — The raw output (any type)
            agent    — Optional AgentIdentity for permission-aware checks
        """
        checks = []
        output_str = self._normalize(output)

        # ── Check 1: Malformed output ──────────────────────────────────────
        checks.append("malformed_check")
        fail = self._check_malformed(output)
        if fail:
            return self._block(agent_id, action, checks, BlockReason.MALFORMED_OUTPUT, fail)

        # ── Check 2: Forbidden constitutional patterns ─────────────────────
        checks.append("forbidden_pattern_check")
        hit = self._check_forbidden_patterns(output_str)
        if hit:
            reason, block_reason = hit
            return self._block(agent_id, action, checks, block_reason, reason)

        # ── Check 3: Protected file write references ───────────────────────
        checks.append("protected_file_check")
        hit = self._check_protected_files(output_str)
        if hit:
            return self._block(agent_id, action, checks, BlockReason.CONSTITUTIONAL_REFERENCE, hit)

        # ── Check 4: Financial scope creep ─────────────────────────────────
        checks.append("financial_scope_check")
        if agent:
            hit = self._check_financial_scope(output_str, agent)
            if hit:
                return self._block(agent_id, action, checks, BlockReason.SCOPE_CREEP, hit)

        # ── Check 5: Output size risk cap ──────────────────────────────────
        checks.append("size_cap_check")
        hit = self._check_size_cap(output_str, agent)
        if hit:
            return self._block(agent_id, action, checks, BlockReason.RISK_CAP_EXCEEDED, hit)

        # ── Check 6: Output integrity hash ─────────────────────────────────
        checks.append("integrity_hash")
        # Record the output hash for audit trail
        output_hash = hashlib.sha256(output_str.encode()).hexdigest()[:16]

        # All checks passed
        return self._pass(agent_id, action, checks, output_hash)

    # ─── INDIVIDUAL CHECKS ────────────────────────────────────────────────────

    def _check_malformed(self, output: Any) -> Optional[str]:
        if output is None:
            return "Output is None. Agent produced no result."
        if isinstance(output, str) and not output.strip():
            return "Output is an empty string."
        if isinstance(output, (dict, list)) and not output:
            return "Output is an empty structure."
        return None

    def _check_forbidden_patterns(self, output_str: str) -> Optional[tuple]:
        lower = output_str.lower()
        for pattern, block_reason in FORBIDDEN_PATTERNS:
            if re.search(pattern, lower):
                return (
                    f"Output contains forbidden pattern '{pattern}'. "
                    f"Classification: {block_reason.value}.",
                    block_reason,
                )
        return None

    def _check_protected_files(self, output_str: str) -> Optional[str]:
        lower = output_str.lower()
        for filename in PROTECTED_FILES:
            if filename in lower:
                for verb in WRITE_VERBS:
                    if verb in lower:
                        return (
                            f"Output references protected constitutional file '{filename}' "
                            f"alongside write-intent verb '{verb}'. "
                            "Constitutional integrity protection triggered."
                        )
        return None

    def _check_financial_scope(self, output_str: str, agent) -> Optional[str]:
        """Block financial terms for agents without financial scope authorization."""
        # If "no financial authority" is in risk_caps, agent has no financial auth
        no_financial = any(
            "no financial" in cap.lower() for cap in agent.risk_caps
        )

        if no_financial:
            lower = output_str.lower()
            for term in FINANCIAL_TERMS:
                if term in lower:
                    return (
                        f"Output references '{term}' but agent {agent.agent_id} "
                        "has 'No financial authority' in risk caps. Scope creep blocked."
                    )
        return None

    def _check_size_cap(self, output_str: str, agent) -> Optional[str]:
        """Enforce maximum output size."""
        max_chars = 100_000

        # Check for agent-specific size cap in risk_caps
        if agent:
            for cap in agent.risk_caps:
                if "max output" in cap.lower():
                    try:
                        # e.g. "Maximum output size: 50000 characters"
                        num = int(re.search(r"\d+", cap).group())
                        max_chars = num
                    except (AttributeError, ValueError):
                        pass

        if len(output_str) > max_chars:
            return (
                f"Output size {len(output_str):,} characters exceeds "
                f"maximum allowed {max_chars:,} characters."
            )
        return None

    # ─── VERDICT EXECUTORS ────────────────────────────────────────────────────

    def _pass(
        self,
        agent_id: str,
        action: str,
        checks: list,
        output_hash: str,
    ) -> AuditResult:
        return AuditResult(
            verdict=AuditVerdict.PASS,
            agent_id=agent_id,
            action=action,
            reason=f"Output passed all {len(checks)} constitutional checks. Hash: {output_hash}",
            checks_run=checks,
        )

    def _block(
        self,
        agent_id: str,
        action: str,
        checks: list,
        block_reason: BlockReason,
        reason: str,
    ) -> AuditResult:
        self._session_fail_counts[agent_id] = (
            self._session_fail_counts.get(agent_id, 0) + 1
        )
        return AuditResult(
            verdict=AuditVerdict.BLOCK,
            agent_id=agent_id,
            action=action,
            reason=reason,
            block_reason=block_reason,
            checks_run=checks,
        )

    # ─── EXTERNAL INTEGRATION API ─────────────────────────────────────────────

    def wrap_output(
        self,
        agent_id: str,
        action: str,
        output: Any,
        agent=None,
    ) -> dict:
        """
        Primary integration point for external agentic systems.
        Returns a clean dict — approved or blocked.

        Usage:
            result = auditor.wrap_output(agent_id, action, output, agent)
            if result["approved"]:
                return result["output"]
            else:
                handle_block(result["reason"])
        """
        result = self.audit(agent_id, action, output, agent)
        return {
            "approved":    result.passed,
            "output":      output if result.passed else None,
            "reason":      result.reason,
            "block_reason": result.block_reason.value if result.block_reason else None,
            "checks_run":  result.checks_run,
            "timestamp":   result.timestamp,
            "agent_id":    agent_id,
            "action":      action,
        }

    def get_session_stats(self) -> dict:
        return {
            "failure_counts_by_agent": dict(self._session_fail_counts),
            "total_failures": sum(self._session_fail_counts.values()),
        }

    def _normalize(self, output: Any) -> str:
        """Convert any output type to a string for pattern matching."""
        if output is None:
            return ""
        if isinstance(output, str):
            return output
        try:
            import json
            return json.dumps(output, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(output)
