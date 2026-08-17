# SDK Guide

How to extend VION Protocol — custom adapters, governance rules, and integrations.

---

## Creating a Custom Adapter

The fastest way to govern any agent is to extend `BaseAgentAdapter`.

```python
from nvion.adapters import BaseAgentAdapter
from typing import Any

class MyAgentAdapter(BaseAgentAdapter):
    """
    Governed adapter for MyAgent.
    Inherits the full 7-stage validation pipeline and N Auditor automatically.
    """

    def __init__(self, my_agent, agent_id: str, orchestrator=None):
        super().__init__(agent_id=agent_id, orchestrator=orchestrator)
        self._agent = my_agent

    def _run_agent(self, action: str, **kwargs) -> Any:
        """
        This is the only method you implement.
        Call your agent here. Everything else is handled by the base class.
        """
        return self._agent.execute(prompt=action)
```

**Usage:**
```python
governed = MyAgentAdapter(
    my_agent=MyAgent(),
    agent_id="VION-RSC-001",
)
result = governed.run(
    auth_token=os.getenv("VION_AUTH_TOKEN"),
    action="search AI papers",
    mode="LIVE",
)
```

---

## Adapter Patterns by Agent Style

### Style A — Object with a method

```python
class MyAdapter(BaseAgentAdapter):
    def _run_agent(self, action, **kwargs):
        return self._agent.run(action)
```

### Style B — Object with a keyword argument

```python
class MyAdapter(BaseAgentAdapter):
    def _run_agent(self, action, **kwargs):
        return self._agent.chat(message=action)
```

### Style C — Callable agent

```python
class MyAdapter(BaseAgentAdapter):
    def _run_agent(self, action, **kwargs):
        return self._agent(action)
```

### Style D — Async agent (wrap with asyncio)

```python
import asyncio

class MyAsyncAdapter(BaseAgentAdapter):
    def _run_agent(self, action, **kwargs):
        return asyncio.run(self._agent.arun(action))
```

### Style E — API call

```python
import requests

class APIAdapter(BaseAgentAdapter):
    def __init__(self, api_url, api_key, agent_id, orchestrator=None):
        super().__init__(agent_id=agent_id, orchestrator=orchestrator)
        self._url = api_url
        self._key = api_key

    def _run_agent(self, action, **kwargs):
        response = requests.post(
            self._url,
            headers={"Authorization": f"Bearer {self._key}"},
            json={"prompt": action},
            timeout=30,
        )
        return response.json()["result"]
```

---

## Adding Custom Audit Rules

Extend `NAuditor` to add domain-specific output checks.

```python
from nvion.core.auditor import NAuditor, AuditResult, AuditVerdict, BlockReason
from typing import Any, Optional

class MyAuditor(NAuditor):
    """
    Extended auditor with custom rules for our deployment.
    """

    # Add custom forbidden patterns
    CUSTOM_PATTERNS = [
        r"internal\s+api\s+key",
        r"production\s+database\s+password",
    ]

    def audit(self, agent_id, action, output, agent=None) -> AuditResult:
        # Run base checks first
        result = super().audit(agent_id, action, output, agent)
        if result.blocked:
            return result

        # Run custom checks
        output_str = self._normalize(output).lower()
        for pattern in self.CUSTOM_PATTERNS:
            import re
            if re.search(pattern, output_str):
                return self._block(
                    agent_id, action,
                    result.checks_run + ["custom_pattern_check"],
                    BlockReason.FORBIDDEN_CONTENT,
                    f"Custom rule: output contains forbidden pattern '{pattern}'",
                )

        return result
```

**Inject into adapter:**
```python
class MyAdapter(BaseAgentAdapter):
    def __init__(self, agent, agent_id, orchestrator=None):
        super().__init__(agent_id=agent_id, orchestrator=orchestrator)
        self._agent = agent
        self._auditor = MyAuditor()  # Override with custom auditor
```

---

## Adding Custom Risk Caps

Extend `RiskCapEvaluator` for domain-specific limits.

```python
from nvion.core.risk_caps import RiskCapEvaluator, CapViolation
from typing import Optional
import re

class MyRiskCapEvaluator(RiskCapEvaluator):

    def evaluate(self, agent_id, action, risk_caps) -> Optional[CapViolation]:
        # Run base evaluation first
        violation = super().evaluate(agent_id, action, risk_caps)
        if violation:
            return violation

        # Custom caps
        action_lower = action.lower()
        for cap in risk_caps:
            cap_lower = cap.lower()

            # Custom: No production database access
            if "no production database" in cap_lower:
                if "production" in action_lower and "database" in action_lower:
                    return CapViolation(
                        cap_text=cap,
                        reason=f"Action targets production database — cap: '{cap}'",
                    )

        return None
```

**Inject into orchestrator:**
```python
orchestrator = Orchestrator()
orchestrator.risk_caps = MyRiskCapEvaluator()
```

---

## Building a Governed Multi-Agent System

```python
import os
from dotenv import load_dotenv
from nvion import NSoul
from nvion.adapters import FunctionAdapter

load_dotenv()

# Boot one governance brain for the whole system
soul = NSoul()
token = os.getenv("VION_AUTH_TOKEN")

# Research agent — read-only
def research(task):
    # your research logic
    return f"Research results for: {task}"

research_agent = FunctionAdapter(
    fn=research,
    agent_id="VION-RSC-001",
    orchestrator=soul._orchestrator,
)

# Execution agent — requires explicit override for LIVE
def execute(task):
    # your execution logic
    return f"Executed: {task}"

execution_agent = FunctionAdapter(
    fn=execute,
    agent_id="VION-EXC-001",
    orchestrator=soul._orchestrator,
)

# Run research
r1 = research_agent.run(token, "find recent AI governance papers", "LIVE")
if r1.ran:
    findings = r1.output

    # Only send to execution if research succeeded
    r2 = execution_agent.run(
        auth_token=token,
        action="generate report from findings",
        mode="LIVE",
        explicit_override=True,  # Required for OVERRIDE_REQUIRED agents
    )
    if r2.ran:
        print("Report:", r2.output)
```

---

## Integrating with FastAPI (REST Gateway)

Expose VION governance as an HTTP endpoint:

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from nvion import NSoul
from nvion.adapters import FunctionAdapter
import os

app = FastAPI(title="VION Protocol Gateway")
soul = NSoul()

class CommandRequest(BaseModel):
    auth_token: str
    target: str
    action: str
    mode: str = "DRY_RUN"

@app.post("/dispatch")
def dispatch(req: CommandRequest):
    governed = FunctionAdapter(
        fn=your_agent_fn,
        agent_id=req.target,
        orchestrator=soul._orchestrator,
    )
    result = governed.run(req.auth_token, req.action, req.mode)
    if not result.approved:
        raise HTTPException(status_code=403, detail=result.blocked_reason)
    return {"output": result.output, "dry_run": result.dry_run}

@app.get("/status")
def status():
    return soul.status()
```

---

## Testing Governed Agents

```python
import pytest
import os
from nvion.adapters import FunctionAdapter
from nvion import NSoul

@pytest.fixture
def soul_env(tmp_path, monkeypatch):
    # Write minimal constitutional documents
    soul_md = tmp_path / "VION.md"
    identity_md = tmp_path / "IDENTITY.md"
    soul_md.write_text("# VION.md\nVersion: 1.0.0")
    identity_md.write_text("""# IDENTITY.md

```
AGENT_ID       : VION-RSC-001
AGENT_NAME     : Test Agent
ROLE           : Research
STATUS         : ACTIVE
REGISTERED     : 2026-01-01
ACTIVATED      : 2026-01-01
AUTH_SCOPE     :
  - Public web sources
PERMISSIONS    :
  - Web search   : EXECUTE
RISK_CAPS      :
  - No financial authority
REPORTS_TO     : VION-ORC-001
PEER_COMMS     : NO
DRY_RUN        : DEFAULT
AUDIT_REQUIRED : YES
NOTES          : Test
```""")

    monkeypatch.setenv("VION_AUTH_TOKEN", "test-token")
    monkeypatch.setenv("SOUL_MD_PATH", str(soul_md))
    monkeypatch.setenv("IDENTITY_MD_PATH", str(identity_md))
    monkeypatch.setenv("LOG_PATH", str(tmp_path / "test.log"))
    return "test-token"

def test_governed_agent_approves_valid_action(soul_env):
    governed = FunctionAdapter(
        fn=lambda task: f"Done: {task}",
        agent_id="VION-RSC-001",
    )
    result = governed.run(soul_env, "search AI papers", "LIVE")
    assert result.approved
    assert result.ran
    assert "Done" in result.output

def test_governed_agent_blocks_wrong_token(soul_env):
    governed = FunctionAdapter(
        fn=lambda task: task,
        agent_id="VION-RSC-001",
    )
    result = governed.run("wrong-token", "search papers", "LIVE")
    assert not result.approved
```

---

## Custom N Auditor Rule Packs

Add domain-specific blocking rules without modifying the base auditor:

```python
from nvion.core.auditor import NAuditor, BlockReason
from nvion.adapters import BaseAgentAdapter

# Define custom patterns (regex, BlockReason)
custom_patterns = [
    (r"internal_api_key\s*=", BlockReason.CREDENTIAL_EXFILTRATION),
    (r"prod_db_password", BlockReason.CREDENTIAL_EXFILTRATION),
    (r"customer_ssn\s*:", BlockReason.FORBIDDEN_CONTENT),
]

# Define custom check functions
def check_pii(output_str: str, agent) -> str | None:
    import re
    if re.search(r"\b\d{3}-\d{2}-\d{4}\b", output_str):
        return "Output contains SSN pattern — PII exfiltration blocked"
    return None

# Attach to your adapter
class MyAdapter(BaseAgentAdapter):
    def __init__(self, agent, agent_id, orchestrator=None):
        super().__init__(agent_id=agent_id, orchestrator=orchestrator)
        self._agent = agent
        self._auditor = NAuditor(
            custom_patterns=custom_patterns,
            custom_checks=[check_pii],
            max_output_chars=50_000,  # Tighter limit for this deployment
        )

    def _run_agent(self, action, **kwargs):
        return self._agent.run(action)
```

## Persistent HALT State

HALT state, suspension state, and condition counts now all persist in `constitution/governance.state`. If the process crashes mid-HALT:

- On next boot, the system reads `governance.state`
- `system_halted: true` means the system boots in HALT — no commands accepted
- Suspended agents remain suspended
- Condition counts are restored

To recover from a crash-HALT:
```python
# Must provide valid Owner token
soul = NSoul()
result = soul.restart(os.getenv("VION_AUTH_TOKEN"))
print(result["message"])
```

Or via CLI:
```bash
python -m nvion.cli
nataw_bot> restart
```
