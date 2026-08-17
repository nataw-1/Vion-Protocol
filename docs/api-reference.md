# API Reference

Complete reference for all public classes, methods, and interfaces.

---

## NSoul

The main integration class. Single entry point for governing any agent system.

```python
from nvion import NSoul
soul = NSoul()
```

### `NSoul.dispatch(auth_token, target, action, mode, explicit_override)`

Dispatch a governed command to a registered agent.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `auth_token` | `str` | ✅ | — | Owner AUTH token |
| `target` | `str` | ✅ | — | Agent ID (e.g. `VION-RSC-001`) |
| `action` | `str` | ✅ | — | Task for the agent |
| `mode` | `str` | — | `DRY_RUN` | `DRY_RUN` or `LIVE` |
| `explicit_override` | `bool` | — | `False` | Required for `OVERRIDE_REQUIRED` agents |

**Returns:** `dict`

```python
{
    "success": True,
    "message": "Command validated and dispatched.",
    "dry_run": False,
}
```

**Example:**
```python
result = soul.dispatch(
    auth_token=os.getenv("VION_AUTH_TOKEN"),
    target="VION-RSC-001",
    action="search recent AI papers",
    mode="LIVE",
)
if result["success"]:
    print("Dispatched")
```

---

### `NSoul.status()`

Returns current system status.

**Returns:** `dict`

```python
{
    "system_halted": False,
    "active_agents": {"VION-RSC-001": {...}},
    "condition_counts": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0},
    "session_id": "A3F2B1C9",
}
```

---

### `NSoul.restart(auth_token)`

Clear a HALT state. Owner only.

**Parameters:**
- `auth_token` — Must match `VION_AUTH_TOKEN`

**Returns:** `dict` — `{"success": True, "message": "..."}`

---

### `NSoul.is_halted()`

Returns `True` if the system is currently halted.

---

### `NSoul.version`

Property. Returns `"1.0.0"`.

---

## Adapters

### BaseAgentAdapter

Abstract base class. Extend this to support any agent framework.

```python
from nvion.adapters import BaseAgentAdapter

class MyAdapter(BaseAgentAdapter):
    def __init__(self, my_agent, agent_id, orchestrator=None):
        super().__init__(agent_id=agent_id, orchestrator=orchestrator)
        self.agent = my_agent

    def _run_agent(self, action: str, **kwargs):
        return self.agent.run(action)
```

#### `BaseAgentAdapter.run(auth_token, action, mode, **kwargs)`

Run the agent under governance.

| Parameter | Type | Description |
|---|---|---|
| `auth_token` | `str` | Owner AUTH token |
| `action` | `str` | Task to execute |
| `mode` | `str` | `DRY_RUN` or `LIVE` |

**Returns:** `AgentRunResult`

---

### AgentRunResult

Dataclass returned by all adapter `run()` calls.

| Field | Type | Description |
|---|---|---|
| `approved` | `bool` | Whether VION approved the command |
| `success` | `bool` | Whether the agent ran successfully |
| `output` | `Any` | Agent output (None if not run) |
| `ran` | `bool` | Whether the agent actually executed |
| `dry_run` | `bool` | Whether this was a dry run |
| `agent_id` | `str` | Which agent ran |
| `action` | `str` | What it was asked to do |
| `mode` | `str` | Execution mode |
| `message` | `str` | Human-readable status |
| `blocked_reason` | `str` | Why blocked (if `approved=False`) |
| `timestamp` | `str` | UTC ISO timestamp |

---

### FunctionAdapter

Wraps any Python function as a governed agent.

```python
from nvion.adapters import FunctionAdapter

governed = FunctionAdapter(
    fn=my_function,          # Callable
    agent_id="VION-RSC-001", # Must match IDENTITY.md
    orchestrator=None,       # Optional: share an orchestrator
)
result = governed.run(token, "search papers", "LIVE")
```

---

### CustomAgentAdapter

Wraps any agent object with a configurable method.

```python
from nvion.adapters import CustomAgentAdapter

governed = CustomAgentAdapter(
    agent=agent_object,
    agent_id="VION-RSC-001",
    call_method="execute",    # Method name on agent
    call_kwarg="prompt",      # Keyword argument name
    orchestrator=None,
)
```

---

### LangChainAdapter

Wraps a LangChain agent or chain.

```python
from nvion.adapters import LangChainAdapter

governed = LangChainAdapter(
    agent=langchain_agent,
    agent_id="VION-RSC-001",
)
result = governed.run(token, "search papers", "LIVE")
```

Internally calls `agent.run(action)` or `agent.invoke({"input": action})`.

---

### CrewAIAdapter

Wraps a CrewAI crew.

```python
from nvion.adapters import CrewAIAdapter

governed = CrewAIAdapter(
    crew=my_crew,
    agent_id="VION-RSC-001",
)
result = governed.run(token, "research task", "LIVE")
```

Internally calls `crew.kickoff(inputs={"task": action})`.

---

### OpenAIAdapter

Wraps direct OpenAI API calls.

```python
from nvion.adapters import OpenAIAdapter
from openai import OpenAI

governed = OpenAIAdapter(
    client=OpenAI(),
    agent_id="VION-RSC-001",
    model="gpt-4o",
    system_prompt="You are a research assistant.",
)
result = governed.run(token, "search AI papers", "LIVE")
```

---

## Core Classes

### Orchestrator

```python
from nvion.core.orchestrator import Orchestrator, OwnerCommand

orc = Orchestrator()
cmd = OwnerCommand(
    auth_token="...",
    target="VION-RSC-001",
    action="search papers",
    mode="LIVE",
    explicit_override=False,
)
result = orc.process_command(cmd)
```

### IdentityRegistry

```python
from nvion.core.identity import IdentityRegistry

registry = IdentityRegistry("./constitution/IDENTITY.md")
agent = registry.get_agent("VION-RSC-001")
registry.suspend_agent("VION-RSC-001", "reason")
registry.reactivate_agent("VION-RSC-001")
registry.reload()
```

### ActivityLogger

```python
from nvion.core.logger import ActivityLogger

logger = ActivityLogger("./logs/activity.log")
logger.verify_chain()           # Raises LogIntegrityError if tampered
entries = logger.read_recent(20)
halts = logger.read_halts()
```

### NAuditor

```python
from nvion.core.auditor import NAuditor

auditor = NAuditor()
result = auditor.audit(agent_id, action, output, agent_identity)
if result.passed:
    deliver(result)
```

### RiskCapEvaluator

```python
from nvion.core.risk_caps import RiskCapEvaluator

evaluator = RiskCapEvaluator()
violation = evaluator.evaluate(agent_id, action, risk_caps_list)
if violation:
    print(violation.reason)  # Condition 5 triggered
```

---

## Exceptions

All exceptions inherit from `NSoulError`.

| Exception | Condition | Description |
|---|---|---|
| `AuthTokenMissingError` | 1 | No token provided |
| `AuthTokenInvalidError` | 1 | Token does not match |
| `AuthTokenExpiredError` | — | Command timestamp too old |
| `AuthNotConfiguredError` | — | VION_AUTH_TOKEN not set |
| `AgentNotFoundError` | 1 | Agent not in IDENTITY.md |
| `AgentSuspendedError` | 1 | Agent is suspended |
| `AgentTerminatedError` | 1 | Agent is terminated |
| `ScopeViolationError` | 2 | Action outside authorized scope |
| `ConstitutionIntegrityError` | 6 | VION.md or IDENTITY.md tampered |
| `LogIntegrityError` | 6 | Log chain broken |
| `SystemHaltedError` | — | Command rejected — system halted |
| `ConfigMissingError` | — | Required env variable missing |
| `HaltConditionTriggeredError` | varies | A HALT condition fired |

**Example error handling:**
```python
from nvion.core.exceptions import (
    AuthTokenInvalidError,
    ScopeViolationError,
    SystemHaltedError,
)

try:
    result = governed.run(token, action, "LIVE")
except SystemHaltedError:
    print("System is halted — Owner must restart")
except ScopeViolationError as e:
    print(f"Scope violation: {e.message}")
```
