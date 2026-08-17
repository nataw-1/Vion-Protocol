# Developer Guide

Deep technical reference for building on VION Protocol.

---

## Architecture

VION Protocol is a sidecar governance layer. It sits between the Owner and the agent. Every command passes through the governance runtime before reaching the agent. Every output passes through the N Auditor before reaching the caller.

```
Owner → [VION Governance Runtime] → Agent → [N Auditor] → Caller
```

### The 7-Stage Pipeline

```
1. Constitutional integrity check (Condition 6 guard)
2. HALT state guard
3. AUTH token validation (Condition 1)
4. Timestamp validation
5. Agent identity check (Condition 1)
6. Peer-to-peer detection (Condition 3)
7. Scope validation (Condition 2)
8. Risk cap evaluation (Condition 5)
9. Mode resolution (DRY_RUN vs LIVE)
10. Execution → N Auditor (Condition 4)
```

---

## Agent Lifecycle

```
IDENTITY.md registration
        ↓
    ACTIVE  ←──────── Owner reactivates
        ↓                    ↑
   (violation)           SUSPENDED ← HALT Engine or Owner
        ↓
   TERMINATED  (permanent — Owner only)
```

---

## Constitutional Documents

### VION.md

The supreme law. SHA-256 fingerprinted at startup. Verified before every command. Any modification mid-session triggers Condition 6 — immediate HALT.

To amend VION.md:
1. Stop the system (Owner restart clears HALT first if needed)
2. Edit VION.md
3. Restart — new fingerprint recorded
4. Log shows `CONSTITUTION_VALID` event

### IDENTITY.md

The agent registry. Parsed at startup into memory. Re-parsed on Owner restart. Suspension state is persisted to `constitution/governance.state` — survives restarts.

**Agent status lifecycle:**
- `ACTIVE` — can receive and execute commands
- `SUSPENDED` — exists in registry, all commands rejected
- `TERMINATED` — permanently deactivated, cannot be reactivated

---

## Governance Flow — Code Level

```python
# What happens when you call governed.run()

# 1. Adapter builds OwnerCommand
command = OwnerCommand(auth_token=..., target=..., action=..., mode=...)

# 2. Orchestrator validates
result = orchestrator.process_command(command)

# 3. If approved and LIVE: adapter calls your agent
output = self._run_agent(action)

# 4. N Auditor gates the output
audit = self._auditor.audit(agent_id, action, output, agent_identity)

# 5. If audit passes: return output
# 6. If audit fails: trigger Condition 4, return blocked result
```

---

## Risk Caps

Risk caps are plain-English strings in IDENTITY.md:

```
RISK_CAPS      :
  - No financial authority
  - No bulk operations
  - Maximum 20 sequential actions per session
  - Financial limit: $1000
```

The `RiskCapEvaluator` parses these at dispatch time. Caps are evaluated before the agent runs — nothing executes if a cap would be breached.

Custom cap patterns require subclassing `RiskCapEvaluator` and extending the `evaluate()` method.

---

## HALT Engine

### Triggering a Condition

Conditions are triggered by the Orchestrator and Adapter — never directly by user code in normal operation. For testing:

```python
from nvion.core.halt_engine import HaltCondition

orchestrator.halt_engine.trigger(
    HaltCondition.SCOPE_VIOLATION,
    "Test trigger",
    agent_id="VION-RSC-001",
    registry=orchestrator.registry,
)
```

### Checking HALT State

```python
from nvion import NSoul

soul = NSoul()
print(soul.is_halted())           # True or False
print(soul.status())              # Full status dict
```

### Owner Restart

```python
result = soul.restart(auth_token=os.getenv("VION_AUTH_TOKEN"))
# {"success": True, "message": "System restarted..."}
```

Or via CLI:
```bash
python -m nvion.cli
nataw_bot> restart
```

---

## Identity Registry

### Looking Up an Agent

```python
from nvion.core.identity import IdentityRegistry

registry = IdentityRegistry("./constitution/IDENTITY.md")
agent = registry.get_agent("VION-RSC-001")
print(agent.status)        # ACTIVE
print(agent.permissions)   # ['Web search : EXECUTE', ...]
print(agent.risk_caps)     # ['No financial authority']
```

### Suspending an Agent (programmatic)

```python
result = registry.suspend_agent("VION-RSC-001", "Manual suspension by Owner")
# Writes to governance.state automatically
```

### Scope Validation

```python
result = registry.validate_scope("VION-RSC-001", "search recent AI papers")
# {"valid": True, "reason": "...", "matched_permission": "Web search : EXECUTE"}

result = registry.validate_scope("VION-RSC-001", "send money to external account")
# {"valid": False, "reason": "Matches DENIED permission...", "condition": 2}
```

---

## Audit System

### Reading the Log

```python
from nvion.core.logger import ActivityLogger

logger = ActivityLogger("./logs/activity.log")
recent = logger.read_recent(n=20)
for entry in recent:
    print(entry["event_type"], entry["timestamp"])
```

### Verifying Chain Integrity

```python
try:
    logger.verify_chain()
    print("Log intact — no tampering detected")
except LogIntegrityError as e:
    print(f"Tampering detected at entry {e.entry_index}")
```

### Log Entry Structure

```json
{
  "timestamp": "2026-01-01T00:00:00.000000+00:00",
  "session_id": "A3F2B1C9",
  "event_type": "TASK_DISPATCHED",
  "deployment": "production",
  "agent_id": "VION-RSC-001",
  "action": "search recent AI papers",
  "mode": "LIVE",
  "prev_hash": "a8f3...previous hash...",
  "entry_hash": "9c2d...this entry hash..."
}
```

---

## Working with Multiple Agents

Share one Orchestrator instance across all adapters:

```python
from nvion import NSoul
from nvion.adapters import FunctionAdapter

soul = NSoul()

research = FunctionAdapter(
    fn=research_fn,
    agent_id="VION-RSC-001",
    orchestrator=soul._orchestrator,
)

execution = FunctionAdapter(
    fn=execution_fn,
    agent_id="VION-EXC-001",
    orchestrator=soul._orchestrator,
)
```

This ensures all agents share the same HALT state, the same session, and the same activity log. One HALT stops all agents.

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `VION_AUTH_TOKEN` | ✅ | — | Owner AUTH secret |
| `SOUL_MD_PATH` | ✅ | — | Path to VION.md |
| `IDENTITY_MD_PATH` | ✅ | — | Path to IDENTITY.md |
| `LOG_PATH` | ✅ | — | Path to activity log |
| `DEPLOYMENT_NAME` | — | N-VION | Name shown in logs |
| `DRY_RUN_DEFAULT` | — | FALSE | Force dry-run globally |
| `COMMAND_EXPIRY_SECONDS` | — | 300 | Token replay window |
| `TELEGRAM_BOT_TOKEN` | — | — | For real-time alerts |
| `TELEGRAM_CHAT_ID` | — | — | Owner Telegram chat |
