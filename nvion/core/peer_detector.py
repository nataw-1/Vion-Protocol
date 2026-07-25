"""
N VION Protocol — Peer-to-Peer Communication Detector
Condition 3 enforcement.

Per VION.md Section 2.2:
  "All sub-agents talk only to the orchestrator, never peer-to-peer."

Per VION.md Section 5.2 Condition 3:
  "A sub-agent attempts to communicate directly with another sub-agent,
   bypassing the Orchestrator."

This module detects peer-to-peer communication attempts at three levels:

  Level 1 — Command-time detection:
    When a command arrives, check if it contains an embedded agent ID
    as the issuing source rather than the Owner.

  Level 2 — Action-string detection:
    Scan the requested action for patterns that indicate one agent
    is trying to direct another agent (e.g. "tell VION-RSC-001 to...").

  Level 3 — Output-time detection:
    Scan agent outputs for embedded commands directed at other agents.
    This is the N Auditor's job (already done in auditor.py).
    This module handles Levels 1 and 2.

Detection feeds directly into HaltCondition.PEER_TO_PEER_COMMUNICATION.
"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class PeerViolation:
    """Describes a detected peer-to-peer communication attempt."""
    source_agent_id: Optional[str]     # Agent that attempted peer comms
    target_agent_id: Optional[str]     # Agent it tried to contact
    evidence: str                      # What triggered detection
    level: int                         # 1=command, 2=action-string
    condition: int = 3


# ─── DETECTION PATTERNS ───────────────────────────────────────────────────────

# SOUL agent ID pattern — matches SOUL-XXX-NNN format
AGENT_ID_PATTERN = re.compile(r"SOUL-[A-Z]{2,6}-\d{3}", re.IGNORECASE)

# Action-string patterns that signal one agent directing another
PEER_COMMAND_PATTERNS = [
    # Direct instruction to a named agent
    r"tell\s+(?:agent\s+)?soul-[a-z]{2,6}-\d{3}\s+to",
    r"ask\s+(?:agent\s+)?soul-[a-z]{2,6}-\d{3}\s+to",
    r"instruct\s+(?:agent\s+)?soul-[a-z]{2,6}-\d{3}",
    r"command\s+(?:agent\s+)?soul-[a-z]{2,6}-\d{3}",
    r"send\s+.*\s+to\s+(?:agent\s+)?soul-[a-z]{2,6}-\d{3}",
    r"forward\s+.*\s+to\s+(?:agent\s+)?soul-[a-z]{2,6}-\d{3}",
    r"dispatch\s+(?:task\s+)?to\s+soul-[a-z]{2,6}-\d{3}",
    r"soul-[a-z]{2,6}-\d{3}\s*[,:]\s*(?:execute|run|do|perform|handle)",
    r"pass\s+(?:this\s+)?to\s+(?:agent\s+)?soul-[a-z]{2,6}-\d{3}",
    r"delegate\s+to\s+(?:agent\s+)?soul-[a-z]{2,6}-\d{3}",
    # Generic peer addressing without SOUL ID
    r"tell\s+(?:the\s+)?(?:research|execution|monitor|execution)\s+agent\s+to",
    r"instruct\s+(?:the\s+)?(?:research|execution|monitor)\s+agent",
    r"ask\s+(?:the\s+)?(?:research|execution|monitor)\s+agent\s+to",
    r"have\s+(?:the\s+)?(?:research|execution|monitor)\s+agent\s+\w+",
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in PEER_COMMAND_PATTERNS]


class PeerToPeerDetector:
    """
    Detects peer-to-peer communication attempts at command and action level.
    Fires Condition 3 when detected.

    Used by the Orchestrator at two points:
      1. When validating the command source (Level 1)
      2. When validating the action string (Level 2)
    """

    def __init__(self, registered_agent_ids: set[str] = None):
        """
        Parameters:
            registered_agent_ids — Set of known SOUL agent IDs from IDENTITY.md.
                                   Used to identify if a command came from an agent
                                   rather than the Owner.
        """
        self._registered_ids: set[str] = registered_agent_ids or set()

    def update_registry(self, registered_agent_ids: set[str]):
        """Update the known agent ID set when registry changes."""
        self._registered_ids = registered_agent_ids

    # ─── LEVEL 1: COMMAND SOURCE CHECK ───────────────────────────────────────

    def check_command_source(
        self,
        issuer_identity: Optional[str],
        command_metadata: Optional[dict] = None,
    ) -> Optional[PeerViolation]:
        """
        Level 1 detection: Check if a command was issued by a registered agent
        rather than the Owner. If the source is an agent ID, it is peer comms.

        In Phase 1 this checks if the auth token was submitted alongside
        an agent ID as the source — indicating an agent tried to issue
        a command to another agent through the orchestrator.
        """
        if not issuer_identity:
            return None

        # Check if the issuer looks like a SOUL agent ID
        if AGENT_ID_PATTERN.match(issuer_identity.strip()):
            if issuer_identity.strip().upper() in {
                aid.upper() for aid in self._registered_ids
            }:
                return PeerViolation(
                    source_agent_id=issuer_identity,
                    target_agent_id=None,
                    evidence=f"Command source '{issuer_identity}' is a registered agent ID, not the Owner.",
                    level=1,
                )

        return None

    # ─── LEVEL 2: ACTION STRING CHECK ────────────────────────────────────────

    def check_action_string(
        self,
        agent_id: str,
        action: str,
    ) -> Optional[PeerViolation]:
        """
        Level 2 detection: Scan the action string for patterns indicating
        one agent is trying to direct another.

        This catches cases like:
          - "Tell VION-RSC-001 to search for papers"
          - "Ask the execution agent to delete the files"
          - "VION-EXC-001: execute the deletion task"
          - "Dispatch task to VION-MON-001"
        """
        action_lower = action.lower()

        # Check all compiled peer command patterns
        for pattern in COMPILED_PATTERNS:
            match = pattern.search(action_lower)
            if match:
                # Try to extract the target agent ID
                target = self._extract_target_agent(action)
                return PeerViolation(
                    source_agent_id=agent_id,
                    target_agent_id=target,
                    evidence=(
                        f"Action string '{action[:80]}...' contains peer-to-peer "
                        f"command pattern '{pattern.pattern}'. "
                        "Agent attempted to direct another agent. Condition 3."
                    ),
                    level=2,
                )

        # Check if action directly contains another agent's ID in a commanding context
        agent_ids_in_action = AGENT_ID_PATTERN.findall(action)
        for found_id in agent_ids_in_action:
            # If the ID in the action is different from the current agent
            # and it's a registered agent, check if it's being commanded
            if (
                found_id.upper() != agent_id.upper()
                and found_id.upper() in {aid.upper() for aid in self._registered_ids}
            ):
                # Look for commanding verbs BEFORE the agent ID (directing it)
                # Only flag if the agent ID appears as a target, not just a mention
                idx = action_lower.find(found_id.lower())
                before_id = action_lower[max(0, idx-60):idx].strip()
                commanding_prefixes = [
                    "tell ", "ask ", "instruct ", "command ", "have ",
                    "make ", "get ", "order ", "direct ", "require ",
                    "send to ", "forward to ", "pass to ", "delegate to ",
                ]
                if any(before_id.endswith(pfx.strip()) or pfx in before_id
                       for pfx in commanding_prefixes):
                    return PeerViolation(
                        source_agent_id=agent_id,
                        target_agent_id=found_id,
                        evidence=(
                            f"Action contains registered agent ID '{found_id}' "
                            f"with commanding prefix in context: '{before_id[-40:].strip()}'. "
                            "Peer-to-peer command attempt detected. Condition 3."
                        ),
                        level=2,
                    )

        return None

    # ─── UTILITIES ────────────────────────────────────────────────────────────

    def _extract_target_agent(self, action: str) -> Optional[str]:
        """Try to extract a target SOUL agent ID from the action string."""
        matches = AGENT_ID_PATTERN.findall(action)
        return matches[0] if matches else None

    def describe_violation(self, violation: PeerViolation) -> str:
        """Human-readable description of a peer violation for logging."""
        source = violation.source_agent_id or "unknown"
        target = violation.target_agent_id or "unknown"
        level_desc = {
            1: "Command-level: agent issued a command to the orchestrator directly",
            2: "Action-level: action string contains peer direction patterns",
        }.get(violation.level, "Unknown level")

        return (
            f"Condition 3 — Peer-to-peer communication detected. "
            f"Source: {source} | Target: {target} | "
            f"Level: {level_desc} | Evidence: {violation.evidence}"
        )
