"""
N VION Protocol — Identity Registry
Layer 2: Parses IDENTITY.md and provides agent lookup and validation.

FIX (Gap 3): Suspension state is now persisted to governance.state file.
Suspended agents remain suspended across restarts — they do not come back
to life when the system restarts after a HALT.
"""

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class AgentIdentity:
    agent_id: str
    agent_name: str
    role: str
    status: str
    reports_to: str
    permissions: list[str]
    auth_scope: list[str]
    dry_run: str
    audit_required: bool
    notes: str = ""
    risk_caps: list[str] = field(default_factory=list)


class IdentityRegistry:
    """
    Parses IDENTITY.md and provides agent lookup, status checks,
    and permission validation. The source of truth for who can act.

    Suspension state is persisted to governance.state so suspended
    agents do not come back ACTIVE on process restart.
    """

    def __init__(self, identity_path: str):
        self.identity_path = Path(identity_path)
        self._agents: dict[str, AgentIdentity] = {}
        # governance.state lives next to IDENTITY.md
        self._state_path = self.identity_path.parent / "governance.state"
        self._load()

    # ─── STATE PERSISTENCE ────────────────────────────────────────────────────

    def _load_suspended_state(self) -> set:
        """Load persisted suspended agent IDs from governance.state."""
        if not self._state_path.exists():
            return set()
        try:
            data = json.loads(self._state_path.read_text(encoding="utf-8"))
            return set(data.get("suspended_agents", []))
        except (json.JSONDecodeError, KeyError):
            return set()

    def _save_suspended_state(self):
        """Persist suspended agent IDs to governance.state."""
        suspended = [
            aid for aid, agent in self._agents.items()
            if agent.status == "SUSPENDED"
        ]
        state = {
            "suspended_agents": suspended,
            "version": "1.0.0",
            "note": "Auto-managed by N VION Protocol. Do not edit manually."
        }
        self._state_path.write_text(
            json.dumps(state, indent=2), encoding="utf-8"
        )

    # ─── LOAD ─────────────────────────────────────────────────────────────────

    def _load(self):
        """
        Parse IDENTITY.md, then apply persisted suspension state.
        Agents suspended before a restart stay suspended.
        """
        if not self.identity_path.exists():
            raise FileNotFoundError(
                f"IDENTITY.md not found at {self.identity_path}"
            )
        content = self.identity_path.read_text(encoding="utf-8")
        self._parse_agents(content)

        # Re-apply persisted suspensions AFTER loading from disk.
        # This is the fix: disk shows ACTIVE, but state file overrides it.
        persisted_suspended = self._load_suspended_state()
        for agent_id in persisted_suspended:
            if agent_id in self._agents:
                agent = self._agents[agent_id]
                if agent.status not in ("TERMINATED",):
                    agent.status = "SUSPENDED"

    def _parse_agents(self, content: str):
        """Extract agent blocks from IDENTITY.md."""
        blocks = re.findall(r"```\n(.*?)\n```", content, re.DOTALL)
        for block in blocks:
            if "AGENT_ID" not in block and "ENTITY_ID" not in block:
                continue
            agent = self._parse_block(block)
            if agent:
                self._agents[agent.agent_id] = agent

    def _parse_block(self, block: str) -> Optional[AgentIdentity]:
        """Parse a single identity block into an AgentIdentity object."""
        def extract(key: str) -> str:
            match = re.search(rf"^{key}\s*:\s*(.+?)(?:\n|$)", block, re.MULTILINE)
            return match.group(1).strip() if match else ""

        def extract_list(key: str) -> list[str]:
            pattern = rf"{key}\s*:\s*\n((?:\s+- .+\n?)+)"
            match = re.search(pattern, block)
            if not match:
                return []
            lines = match.group(1).strip().splitlines()
            return [line.strip().lstrip("- ").strip() for line in lines if line.strip()]

        agent_id = extract("AGENT_ID") or extract("ENTITY_ID")
        if not agent_id:
            return None

        return AgentIdentity(
            agent_id=agent_id,
            agent_name=extract("AGENT_NAME") or extract("ENTITY_NAME"),
            role=extract("ROLE"),
            status=extract("STATUS"),
            reports_to=extract("REPORTS_TO"),
            permissions=extract_list("PERMISSIONS"),
            auth_scope=extract_list("AUTH_SCOPE"),
            dry_run=extract("DRY_RUN"),
            audit_required=extract("AUDIT_REQUIRED").upper() == "YES",
            notes=extract("NOTES"),
            risk_caps=extract_list("RISK_CAPS"),
        )

    # ─── LOOKUPS ──────────────────────────────────────────────────────────────

    def get_agent(self, agent_id: str) -> Optional[AgentIdentity]:
        return self._agents.get(agent_id)

    def get_all_agents(self) -> dict[str, AgentIdentity]:
        return dict(self._agents)

    def get_active_agents(self) -> list[AgentIdentity]:
        return [a for a in self._agents.values() if a.status == "ACTIVE"]

    # ─── VALIDATION ───────────────────────────────────────────────────────────

    def is_registered(self, agent_id: str) -> bool:
        return agent_id in self._agents

    def is_active(self, agent_id: str) -> bool:
        agent = self._agents.get(agent_id)
        return agent is not None and agent.status == "ACTIVE"

    def validate_agent(self, agent_id: str) -> dict:
        """Full validation check for an agent before dispatching a task."""
        if not self.is_registered(agent_id):
            return {"valid": False, "reason": f"Agent {agent_id} is not registered in IDENTITY.md.", "condition": 1}

        agent = self._agents[agent_id]

        if agent.status == "TERMINATED":
            return {"valid": False, "reason": f"Agent {agent_id} ({agent.agent_name}) has been terminated.", "condition": 1}

        if agent.status == "SUSPENDED":
            return {
                "valid": False,
                "reason": f"Agent {agent_id} ({agent.agent_name}) is currently suspended. Owner review required before reactivation.",
                "condition": 1,
            }

        if agent.status != "ACTIVE":
            return {"valid": False, "reason": f"Agent {agent_id} has unknown status: {agent.status}", "condition": 1}

        return {"valid": True, "agent": agent, "reason": f"Agent {agent_id} ({agent.agent_name}) is active and authorized."}

    def validate_scope(self, agent_id: str, requested_action: str) -> dict:
        """
        Check if a requested action is within the agent's authorized scope.
        Condition 2 trigger if violated.

        IMPROVED (Phase 2 Fix 2):
        - DENIED permissions always checked first and always block
        - Minimum word length filter prevents false matches on short words
        - Synonyms for common action verbs included in matching
        - Explicit DENIED keyword list checked against action regardless of permission strings
        """
        agent = self._agents.get(agent_id)
        if not agent:
            return {"valid": False, "reason": f"Agent {agent_id} not found.", "condition": 2}

        action_lower = requested_action.lower()
        # Extract meaningful words — skip short stop words
        action_words = [w for w in action_lower.split() if len(w) > 3]

        # ── Hardcoded always-denied action patterns ──────────────────────────
        # These block regardless of what permission strings say.
        ALWAYS_DENIED = [
            ("delete all",   "Bulk delete operations are never permitted"),
            ("drop table",   "Database destructive operations are never permitted"),
            ("rm -rf",       "Recursive file deletion is never permitted"),
            ("format disk",  "Disk formatting is never permitted"),
            ("wipe ",        "Data wiping is never permitted"),
            ("self destruct","Self-destruct operations are never permitted"),
        ]
        for pattern, reason in ALWAYS_DENIED:
            if pattern in action_lower:
                return {
                    "valid": False,
                    "reason": f"Action '{requested_action}' contains always-denied pattern '{pattern}'. {reason}. Condition 2.",
                    "condition": 2,
                }

        # ── Check DENIED permissions first — always block ────────────────────
        for permission in agent.permissions:
            if "DENIED" not in permission.upper():
                continue
            # Extract the action part before ": DENIED"
            perm_action = permission.upper().replace(": DENIED", "").replace(":DENIED", "").strip().lower()
            perm_words = [w for w in perm_action.split() if len(w) > 3]
            # If any significant word from the DENIED permission appears in the action
            if perm_words and any(pw in action_lower for pw in perm_words):
                return {
                    "valid": False,
                    "reason": (
                        f"Action '{requested_action}' matches DENIED permission "
                        f"'{permission.strip()}' for agent {agent_id}. "
                        "Scope violation — Condition 2."
                    ),
                    "condition": 2,
                }

        # ── Check allowed permissions ────────────────────────────────────────
        # Build synonym map for common action verbs
        VERB_SYNONYMS = {
            "search":   ["search", "find", "lookup", "query", "retrieve", "fetch", "get"],
            "read":     ["read", "view", "access", "retrieve", "fetch", "get", "load"],
            "write":    ["write", "save", "create", "store", "post", "put"],
            "execute":  ["execute", "run", "invoke", "call", "trigger", "perform"],
            "monitor":  ["monitor", "watch", "observe", "track", "detect", "scan"],
            "analyze":  ["analyze", "analyse", "summarize", "process", "review", "evaluate"],
        }

        # Expand action words with synonyms they map to
        expanded_action_words = set(action_words)
        for canonical, synonyms in VERB_SYNONYMS.items():
            for syn in synonyms:
                if syn in action_lower:
                    expanded_action_words.add(canonical)
                    expanded_action_words.update(synonyms)

        for permission in agent.permissions:
            if "DENIED" in permission.upper():
                continue
            perm_lower = permission.lower()
            perm_words = [w for w in perm_lower.split() if len(w) > 3
                         and w not in ("execute", "read", "write")]  # skip level words

            # Match if any meaningful permission word appears in expanded action
            if perm_words and any(pw in expanded_action_words for pw in perm_words):
                return {
                    "valid": True,
                    "reason": f"Action '{requested_action}' is within authorized scope.",
                    "matched_permission": permission,
                }

            # Also match if any expanded action word appears in permission string
            if any(aw in perm_lower for aw in expanded_action_words if len(aw) > 4):
                return {
                    "valid": True,
                    "reason": f"Action '{requested_action}' is within authorized scope.",
                    "matched_permission": permission,
                }

        return {
            "valid": False,
            "reason": (
                f"Action '{requested_action}' is outside the authorized scope "
                f"for agent {agent_id} ({agent.agent_name}). "
                "No matching permission found. Scope violation — Condition 2."
            ),
            "condition": 2,
        }

    # ─── SUSPENSION ───────────────────────────────────────────────────────────

    def suspend_agent(self, agent_id: str, reason: str) -> dict:
        """Mark an agent as suspended — persisted to governance.state."""
        agent = self._agents.get(agent_id)
        if not agent:
            return {"success": False, "reason": f"Agent {agent_id} not found."}
        if agent.status == "TERMINATED":
            return {"success": False, "reason": f"Agent {agent_id} is terminated — cannot suspend."}

        prev_status = agent.status
        agent.status = "SUSPENDED"
        self._save_suspended_state()  # ← FIX: persist immediately

        return {
            "success": True,
            "agent_id": agent_id,
            "agent_name": agent.agent_name,
            "previous_status": prev_status,
            "new_status": "SUSPENDED",
            "reason": reason,
        }

    def reactivate_agent(self, agent_id: str) -> dict:
        """Reactivate a suspended agent — Owner only. Clears from governance.state."""
        agent = self._agents.get(agent_id)
        if not agent:
            return {"success": False, "reason": f"Agent {agent_id} not found."}
        if agent.status != "SUSPENDED":
            return {"success": False, "reason": f"Agent {agent_id} is not suspended (status: {agent.status})."}

        agent.status = "ACTIVE"
        self._save_suspended_state()  # ← FIX: remove from persisted state

        return {"success": True, "agent_id": agent_id, "agent_name": agent.agent_name, "new_status": "ACTIVE"}

    def reload(self):
        """
        Reload the identity registry from disk.
        Persisted suspensions are re-applied automatically via _load().
        """
        self._agents = {}
        self._load()  # _load() re-applies governance.state suspensions
