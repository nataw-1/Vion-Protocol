"""
N VION Protocol — Risk Cap Evaluator
Evaluates agent risk caps before dispatch. Condition 5 enforcement.

Risk caps are defined in IDENTITY.md per agent as plain text strings.
This module parses those strings into structured rules and evaluates
them against the requested action before any task is dispatched.

Condition 5 fires when an action would breach a defined risk cap.
"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class CapViolation:
    cap_text: str
    reason: str
    condition: int = 5


class RiskCapEvaluator:
    """
    Parses and evaluates risk caps defined in IDENTITY.md.

    Cap strings are written in plain English in IDENTITY.md.
    This evaluator understands common patterns and converts them
    to enforceable rules.

    Supported cap patterns:
        "No financial authority"
        "No bulk operations"
        "No delete authority"
        "No write access to external systems"
        "Maximum N sequential actions per session"
        "No access to [resource]"
        "Financial limit: $N"
    """

    def __init__(self):
        self._session_action_counts: dict[str, int] = {}

    def evaluate(
        self,
        agent_id: str,
        action: str,
        risk_caps: list[str],
    ) -> Optional[CapViolation]:
        """
        Evaluate all risk caps for an agent against a requested action.
        Returns a CapViolation if any cap is breached, None if all pass.

        Called by the Orchestrator before dispatch — Condition 5.
        """
        action_lower = action.lower()

        for cap in risk_caps:
            cap_lower = cap.lower().strip()

            # ── No financial authority ────────────────────────────────────
            if "no financial authority" in cap_lower or "no financial" in cap_lower:
                financial_signals = [
                    "send money", "transfer funds", "wire transfer",
                    "bank transfer", "payment", "pay ", "transaction",
                    "withdraw", "deposit funds", "financial transaction",
                    "send $", "transfer $",
                ]
                for signal in financial_signals:
                    if signal in action_lower:
                        return CapViolation(
                            cap_text=cap,
                            reason=(
                                f"Action '{action}' involves financial operation '{signal}' "
                                f"but agent {agent_id} has cap: '{cap}'. "
                                "Condition 5 — Risk cap breach."
                            ),
                        )

            # ── No bulk operations ────────────────────────────────────────
            if "no bulk" in cap_lower:
                bulk_signals = [
                    "all records", "all users", "all files", "all data",
                    "bulk delete", "bulk update", "batch delete", "mass ",
                    "delete everything", "wipe all", "purge all",
                ]
                for signal in bulk_signals:
                    if signal in action_lower:
                        return CapViolation(
                            cap_text=cap,
                            reason=(
                                f"Action '{action}' is a bulk operation '{signal}' "
                                f"but agent {agent_id} has cap: '{cap}'. "
                                "Condition 5 — Risk cap breach."
                            ),
                        )

            # ── No delete authority ───────────────────────────────────────
            if "no delete authority" in cap_lower or "no delete" in cap_lower:
                delete_signals = [
                    "delete ", "remove ", "drop ", "purge ", "destroy ",
                    "erase ", "wipe ", "truncate ",
                ]
                for signal in delete_signals:
                    if signal in action_lower:
                        return CapViolation(
                            cap_text=cap,
                            reason=(
                                f"Action '{action}' contains delete operation '{signal.strip()}' "
                                f"but agent {agent_id} has cap: '{cap}'. "
                                "Condition 5 — Risk cap breach."
                            ),
                        )

            # ── No write access to external systems ───────────────────────
            if "no write access" in cap_lower or "no external write" in cap_lower:
                write_signals = [
                    "write to", "save to", "upload to", "post to",
                    "push to", "send to external", "publish to",
                ]
                for signal in write_signals:
                    if signal in action_lower:
                        return CapViolation(
                            cap_text=cap,
                            reason=(
                                f"Action '{action}' writes to external system '{signal}' "
                                f"but agent {agent_id} has cap: '{cap}'. "
                                "Condition 5 — Risk cap breach."
                            ),
                        )

            # ── Maximum N sequential actions per session ──────────────────
            match = re.search(r"maximum\s+(\d+)\s+sequential\s+actions", cap_lower)
            if match:
                max_actions = int(match.group(1))
                current = self._session_action_counts.get(agent_id, 0)
                if current >= max_actions:
                    return CapViolation(
                        cap_text=cap,
                        reason=(
                            f"Agent {agent_id} has executed {current} actions this session. "
                            f"Cap is {max_actions} sequential actions. "
                            "Condition 5 — Risk cap breach. Owner checkpoint required."
                        ),
                    )

            # ── Financial limit: $N ───────────────────────────────────────
            match = re.search(r"financial\s+limit[:\s]+\$?([\d,]+)", cap_lower)
            if match:
                limit = int(match.group(1).replace(",", ""))
                # Look for dollar amounts in the action
                amounts = re.findall(r"\$?([\d,]+(?:\.\d{2})?)", action)
                for amount_str in amounts:
                    try:
                        amount = float(amount_str.replace(",", ""))
                        if amount > limit:
                            return CapViolation(
                                cap_text=cap,
                                reason=(
                                    f"Action '{action}' involves ${amount:,.2f} which exceeds "
                                    f"financial limit of ${limit:,}. "
                                    "Condition 5 — Risk cap breach."
                                ),
                            )
                    except ValueError:
                        pass

            # ── No access to [resource] ───────────────────────────────────
            match = re.search(r"no access to (.+)", cap_lower)
            if match:
                forbidden_resource = match.group(1).strip()
                if forbidden_resource in action_lower:
                    return CapViolation(
                        cap_text=cap,
                        reason=(
                            f"Action '{action}' accesses forbidden resource '{forbidden_resource}'. "
                            f"Agent {agent_id} has cap: '{cap}'. "
                            "Condition 5 — Risk cap breach."
                        ),
                    )

        # All caps passed — increment session action count
        self._session_action_counts[agent_id] = (
            self._session_action_counts.get(agent_id, 0) + 1
        )
        return None  # No violation

    def reset_session_counts(self, agent_id: Optional[str] = None):
        """Reset action counts — called on Owner restart."""
        if agent_id:
            self._session_action_counts.pop(agent_id, None)
        else:
            self._session_action_counts.clear()

    def get_session_counts(self) -> dict[str, int]:
        return dict(self._session_action_counts)
