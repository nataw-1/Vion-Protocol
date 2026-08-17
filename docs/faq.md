# Frequently Asked Questions

---

## What is VION Protocol?

VION Protocol is a constitutional governance runtime for autonomous AI agents. It sits between an Owner and their agents and validates every command before execution. It ensures agents only do what they are authorized to do, logs everything permanently, and autonomously stops the system if any rule is violated.

---

## Why does it exist?

AI agents are being deployed into production systems with real access — to databases, APIs, financial systems, and private data. But the tools for governing them are either missing or inadequate. Most governance today is either a system prompt (which can be ignored) or a human watching a dashboard (which does not scale). VION Protocol is infrastructure-grade governance — law that runs automatically, enforces itself, and proves compliance through a tamper-evident audit trail.

---

## How is VION Protocol different from Guardrails AI?

Guardrails AI validates inputs and outputs against schema rules. It is a data validation layer. VION Protocol is a constitutional governance layer. VION governs *authority* (who can issue commands), *identity* (who the agents are), *scope* (what they are allowed to do), and *enforcement* (what happens when rules are violated). Guardrails has no concept of agent identity, no kill-switch, and no audit chain. VION Protocol has all of these.

---

## How is it different from Constitutional AI (Anthropic)?

Constitutional AI (CAI) is a training methodology — a technique for fine-tuning language models to follow a set of principles. It operates at the model level, before deployment. VION Protocol is a runtime enforcement layer — it operates after deployment, around any model or agent, regardless of how that model was trained. You can use VION Protocol on top of Claude, GPT-4, Llama, or any other model.

---

## How is it different from LangChain?

LangChain is an agent framework — a toolkit for building agents with tools, memory, and chains. VION Protocol is a governance layer that wraps agent frameworks. They are complementary. You use LangChain to build your agent, then wrap it with VION Protocol to govern it. VION has a `LangChainAdapter` specifically for this.

---

## How is it different from CrewAI?

CrewAI is a multi-agent orchestration framework. VION Protocol is a governance layer. You use CrewAI to define agent roles and workflows, then govern the whole crew with VION Protocol through the `CrewAIAdapter`. VION adds constitutional law, identity verification, and the HALT Engine on top of CrewAI's orchestration.

---

## How does the HALT Engine work?

The HALT Engine monitors 6 conditions defined in the VION.md constitution. When a condition is triggered, it responds in one of two ways:

**ESCALATE** — The affected agent is suspended, the event is logged, and the Owner receives a Telegram alert. The system continues running for other agents.

**HALT** — All agents are suspended, all pending commands are rejected, and the Owner receives a critical alert. The system is completely locked until the Owner issues a restart.

The HALT Engine fires autonomously — no human intervention required. On the third unauthorized command attempt, the system halts itself.

---

## Can VION Protocol stop dangerous actions?

Yes. Within the governance model, VION Protocol will block:
- Any command from an unauthorized source
- Any action outside an agent's registered scope
- Any action that breaches a defined risk cap (e.g. financial operations for agents without financial authority)
- Any agent output containing self-modification attempts, credential leaks, or peer-to-peer commands
- Direct agent-to-agent communication bypassing the Orchestrator
- Any modification to the constitutional documents mid-session

It does not sandbox execution at the OS level. If an agent has access to dangerous tools and those tools are within its authorized scope, VION Protocol will allow their use. The constitutional documents define the limits.

---

## Is VION Protocol production ready?

VION Protocol v1.0.0 is production-ready for pre-execution governance, identity validation, scope enforcement, risk cap evaluation, output auditing, and tamper-evident logging. It is used internally by N Nexus.

Known limitations in v1.0.0:
- HALT state resets on process crash (mitigated by governance.state persistence)
- No built-in rate limiting on AUTH attempts beyond HALT after 3 failures
- No sandboxing of agent execution environments
- Telegram delivery is best-effort (fails silently if unconfigured)

These are addressed in the v1.1.0 and v1.2.0 roadmap items.

---

## What license does VION Protocol use?

MIT License. You can use it, modify it, and build commercial products on top of it. Attribution is appreciated but not required.

---

## How do I register an agent?

Add a registration block to `constitution/IDENTITY.md`:

```
AGENT_ID       : VION-XXX-001
AGENT_NAME     : My Agent
ROLE           : What this agent does
STATUS         : ACTIVE
REGISTERED     : 2026-01-01
ACTIVATED      : 2026-01-01
AUTH_SCOPE     :
  - What systems it can access
PERMISSIONS    :
  - Allowed action              : EXECUTE
  - Forbidden action            : DENIED
RISK_CAPS      :
  - No financial authority
REPORTS_TO     : VION-ORC-001
PEER_COMMS     : NO
DRY_RUN        : DEFAULT
AUDIT_REQUIRED : YES
NOTES          : Description
```

Then restart the system to reload the registry.

---

## What happens when the system is HALTed?

All agents are suspended. Every command is rejected with `SystemHaltedError`. The activity log records the HALT event. The Owner receives a Telegram alert. To restore operations, the Owner must call `soul.restart(auth_token)` or run `python -m nvion.cli` and type `restart`. All suspension states and condition counts are reset on restart.

---

## Can I use VION Protocol without Telegram?

Yes. Telegram is optional. If `TELEGRAM_BOT_TOKEN` is not set, the system runs normally and all alerts are silently skipped. You can still check the activity log and use the CLI to monitor governance state.

---

## How do I verify the audit log has not been tampered with?

```python
from nvion.core.logger import ActivityLogger
from nvion.core.exceptions import LogIntegrityError

logger = ActivityLogger("./logs/activity.log")
try:
    logger.verify_chain()
    print("Log is intact — no tampering detected")
except LogIntegrityError as e:
    print(f"Tampering detected at entry index {e.entry_index}")
```

Or via CLI:
```bash
python -m nvion.cli
nataw_bot> logs
```

---

## Can multiple agents share the same governance instance?

Yes — and they should. Pass the same `orchestrator` instance to all adapters. This ensures all agents share the same HALT state, session ID, and activity log:

```python
soul = NSoul()
agent1 = FunctionAdapter(fn=fn1, agent_id="VION-RSC-001", orchestrator=soul._orchestrator)
agent2 = FunctionAdapter(fn=fn2, agent_id="VION-EXC-001", orchestrator=soul._orchestrator)
```
