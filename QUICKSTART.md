# N VION Protocol — 5-Minute Quickstart

Get N VION Protocol governing your first agent in under 5 minutes.

---

## What you need
- Python 3.11 or higher
- A terminal
- Any Python agent (or use the mock below)

---

## Step 1 — Clone and install (60 seconds)

```bash
git clone https://github.com/YOUR_USERNAME/N-Soul-Protocol
cd N-Soul-Protocol
pip install -r requirements.txt
```

---

## Step 2 — Configure (30 seconds)

```bash
copy .env.example .env      # Windows
# cp .env.example .env      # Mac/Linux
```

Open `.env` and set at minimum:

```env
VION_AUTH_TOKEN=mysecrettoken123
SOUL_MD_PATH=./constitution/VION.md
IDENTITY_MD_PATH=./constitution/IDENTITY.md
LOG_PATH=./logs/activity.log
DRY_RUN_DEFAULT=TRUE
```

---

## Step 3 — Register your agent (60 seconds)

Open `constitution/IDENTITY.md`, scroll to **Section 6**, and add your agent:

```
AGENT_ID       : VION-MY-001
AGENT_NAME     : My First Agent
ROLE           : Research and web search
STATUS         : ACTIVE
REGISTERED     : 2026-01-01
ACTIVATED      : 2026-01-01
AUTH_SCOPE     :
  - Public web sources
PERMISSIONS    :
  - Web search                      : EXECUTE
  - Public data retrieval           : READ
RISK_CAPS      :
  - No financial authority
REPORTS_TO     : VION-ORC-001
PEER_COMMS     : NO
DRY_RUN        : DEFAULT
AUDIT_REQUIRED : YES
NOTES          : My first governed agent
```

---

## Step 4 — Govern your agent (60 seconds)

Create `govern.py` in your project:

```python
import os, sys
sys.path.insert(0, "path/to/N-Soul-Protocol")

from dotenv import load_dotenv
load_dotenv("path/to/N-Soul-Protocol/.env")

from nvion.adapters import FunctionAdapter

# Your agent — replace with your real agent call
def my_agent(task: str) -> str:
    return f"Result for: {task}"

# Wrap it with N-VION governance
governed = FunctionAdapter(
    fn=my_agent,
    agent_id="VION-MY-001",
)

# Run — every task now passes through the full governance pipeline
result = governed.run(
    auth_token=os.getenv("VION_AUTH_TOKEN"),
    action="search recent AI papers",
    mode="LIVE",
)

if result.ran:
    print("Output:", result.output)
else:
    print("Blocked:", result.blocked_reason)
```

```bash
python govern.py
```

---

## Step 5 — Run the Owner CLI (optional)

```bash
python -m nvion.cli
```

Then type:
```
nataw_bot> status          # see all agents
nataw_bot> dispatch        # issue a command interactively
nataw_bot> logs            # see the full audit trail
```

---

## Step 6 — Run the demo

```bash
python examples/demo.py
```

Watch N-VION block a financial transaction and a delete operation in real time.

---

## What just happened

Every time `governed.run()` is called, N VION Protocol:

1. Validated your AUTH token
2. Checked the agent exists and is ACTIVE in IDENTITY.md
3. Validated the action is within the agent's authorized scope
4. Enforced dry-run or live execution
5. Logged everything to `logs/activity.log` with a tamper-evident hash chain
6. Would have fired a HALT and Telegram alert if anything violated the constitution

Your agent is now constitutionally governed.

---

## Connecting a real agent (OpenClaw, Hermes, LangChain, etc.)

```python
from nvion.adapters import CustomAgentAdapter

# Style A — agent.run(action)
governed = CustomAgentAdapter(
    agent=your_agent,
    agent_id="VION-MY-001",
    call_method="run",
)

# Style B — agent.execute(prompt=action)
governed = CustomAgentAdapter(
    agent=your_agent,
    agent_id="VION-MY-001",
    call_method="execute",
    call_kwarg="prompt",
)

# Style C — extend BaseAgentAdapter for full control
from nvion.adapters import BaseAgentAdapter

class MyAdapter(BaseAgentAdapter):
    def _run_agent(self, action, **kwargs):
        return self.my_agent.chat(action)
```

---

## Next steps

- Read the full [README](./README.md) for architecture details
- Check [IDENTITY.md](./constitution/IDENTITY.md) to register more agents
- Read [VION.md](./constitution/VION.md) to understand your constitutional law
- Run `pytest tests/` to verify everything is working
