# Getting Started with VION Protocol

Get your first agent governed in under 10 minutes.

---

## Prerequisites

- Python 3.11 or higher
- pip
- A terminal

---

## Step 1 — Install

```bash
pip install nvion-protocol
```

Verify installation:
```bash
python -c "from nvion import NSoul; print('VION Protocol ready')"
```

---

## Step 2 — Configure

Create a `.env` file in your project root:

```env
VION_AUTH_TOKEN=your-secret-token-here
SOUL_MD_PATH=./constitution/VION.md
IDENTITY_MD_PATH=./constitution/IDENTITY.md
LOG_PATH=./logs/activity.log
DRY_RUN_DEFAULT=TRUE
DEPLOYMENT_NAME=my-deployment
```

Generate a secure token:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Step 3 — Create Constitutional Documents

Create `constitution/VION.md`:

```markdown
# VION.md — Constitutional Law
Version: 1.0.0
Issued by: [Your Name]
Deployment: [Your Deployment Name]

This document is the supreme law governing all agents in this deployment.
```

Create `constitution/IDENTITY.md` with your first agent:

```
# IDENTITY.md — Agent Registry

```
AGENT_ID       : VION-RSC-001
AGENT_NAME     : My Research Agent
ROLE           : Research and web retrieval
STATUS         : ACTIVE
REGISTERED     : 2026-01-01
ACTIVATED      : 2026-01-01
AUTH_SCOPE     :
  - Public web sources
  - Internal knowledge base
PERMISSIONS    :
  - Web search                      : EXECUTE
  - Public data retrieval           : READ
  - Financial transactions          : DENIED
RISK_CAPS      :
  - No financial authority
REPORTS_TO     : VION-ORC-001
PEER_COMMS     : NO
DRY_RUN        : DEFAULT
AUDIT_REQUIRED : YES
NOTES          : My first governed agent
```
```

---

## Step 4 — Govern Your First Agent

Create `govern.py`:

```python
import os
from dotenv import load_dotenv
from nvion import NSoul
from nvion.adapters import FunctionAdapter

load_dotenv()

# Your agent — replace with your real agent
def my_agent(task: str) -> str:
    return f"Research complete for: {task}"

# Wrap with VION governance
governed = FunctionAdapter(
    fn=my_agent,
    agent_id="VION-RSC-001",
)

# Test in dry-run first
result = governed.run(
    auth_token=os.getenv("VION_AUTH_TOKEN"),
    action="search recent AI papers",
    mode="DRY_RUN",
)

print("Approved:", result.approved)
print("Message:", result.message)
```

Run it:
```bash
python govern.py
```

Expected output:
```
Approved: True
Message: [DRY RUN] Command approved. Agent VION-RSC-001 is authorized for: search recent AI papers
```

---

## Step 5 — Run Live

Change `mode="DRY_RUN"` to `mode="LIVE"` and run again. Your agent now executes under full constitutional governance.

---

## Step 6 — Run the Demo

```bash
python examples/demo.py
```

Watch VION Protocol:
- Approve a valid research task
- Block a financial transaction
- Block a delete operation
- Reject a wrong AUTH token
- Print the full tamper-evident audit trail

---

## Common Mistakes

**"Agent not registered in IDENTITY.md"**
The `agent_id` in your code must match exactly what is in IDENTITY.md — case-sensitive, including hyphens.

**"AUTH token is invalid"**
Check that `VION_AUTH_TOKEN` in your `.env` matches exactly what you pass as `auth_token` in code. No extra spaces.

**"System is HALTED"**
A violation triggered a HALT. Run the CLI and restart:
```bash
python -m nvion.cli
nataw_bot> restart
```

**"Action is outside authorized scope"**
Add the action type to `AUTH_SCOPE` or `PERMISSIONS` in IDENTITY.md for your agent.

---

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: nvion` | Package not installed | `pip install nvion-protocol` |
| `VION.md not found` | Wrong path in .env | Check `SOUL_MD_PATH` in .env |
| `VION_AUTH_TOKEN not configured` | Missing .env variable | Add `VION_AUTH_TOKEN=...` to .env |
| `Agent is suspended` | Previous HALT suspended agent | Run CLI → restart |
| `Command expired` | Timestamp too old | Check system clock, reduce latency |
