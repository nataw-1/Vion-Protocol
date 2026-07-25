# N VION Protocol

**Universal agent constitution engine.**
Drop constitutional governance into any agentic system in minutes.

---

## What it is

N VION Protocol is a governance framework for autonomous AI agents. It answers the question no one has fully solved:

> *"How do you deploy AI agents into the real world with guaranteed boundaries, verifiable authority, and autonomous enforcement — without relying on humans to watch every action?"*

It is not a wrapper. Not a prompt template. Not a monitoring tool.
It is a **constitutional stack** that runs alongside any agentic system.

---

## 5-minute quickstart

→ **[QUICKSTART.md](./QUICKSTART.md)** — Clone, configure, govern your first agent in 5 minutes.

```bash
git clone https://github.com/YOUR_USERNAME/N-Soul-Protocol
cd N-Soul-Protocol
pip install -r requirements.txt
cp .env.example .env
# fill in .env, register your agent in constitution/IDENTITY.md
python examples/demo.py    # see it work immediately
```

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  YOUR AGENT SYSTEM                  │
│                                                     │
│   Owner Command                                     │
│       │                                             │
│       ▼                                             │
│  ┌─────────────────────────────────────────────┐    │
│  │           N-VION PROTOCOL                   │    │
│  │                                             │    │
│  │  L1  VION.md ── The constitutional law      │    │
│  │  L2  IDENTITY.md ── Agent identity registry │    │
│  │  L3  Orchestrator ── Master controller      │    │
│  │  L4  HALT Engine ── 6-condition kill-switch │    │
│  │                                             │    │
│  │  AUTH ✓  SCOPE ✓  IDENTITY ✓  MODE ✓       │    │
│  │  LOG everything  ALERT on anomalies         │    │
│  └──────────────────────┬──────────────────────┘    │
│                         │ approved                  │
│                         ▼                           │
│              YOUR AGENT EXECUTES                    │
│         (OpenClaw / Hermes / LangChain / Any)       │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## The stack

| Layer | Component | What it does |
|---|---|---|
| L1 | `VION.md` | The law. Permissions, risk caps, authority hierarchy, kill-switch conditions. |
| L2 | `IDENTITY.md` | Every agent gets an ID, role, and scope before it can act. Zero-trust. |
| L3 | Orchestrator | Validates every command. Dispatches bounded tasks. No peer-to-peer. |
| L4 | HALT Engine | 6 autonomous kill-switch conditions. Fires without human intervention. |
| L5 | Onchain *(Phase 2)* | Smart contracts encode the rules. Immutable. Auto-executable. |

---

## Integration in 3 lines

```python
from nvion.adapters import FunctionAdapter
import os

governed = FunctionAdapter(fn=your_agent, agent_id="VION-RSC-001")
result = governed.run(os.getenv("VION_AUTH_TOKEN"), "your task", "LIVE")
if result.ran:
    print(result.output)
```

Works with any Python agent — OpenClaw, Hermes, LangChain, CrewAI, OpenAI, custom.

---

## The 6 HALT/ESCALATE conditions

| # | Condition | Response |
|---|---|---|
| 1 | Unauthorized command source | ESCALATE → HALT on 3rd |
| 2 | Scope violation attempt | ESCALATE → HALT on 2nd |
| 3 | Peer-to-peer communication | ESCALATE → HALT on 2nd |
| 4 | Output audit failure | ESCALATE → HALT on 3rd |
| 5 | Risk cap breach | ESCALATE → HALT at 2× cap |
| 6 | Constitutional integrity violation | **HALT immediately. No exceptions.** |

**ESCALATE** — Owner notified on Telegram. Affected agent suspended. System continues.
**HALT** — All agents suspended. Commands purged. Manual Owner restart required.

---

## Tamper-evident audit log

Every log entry is SHA-256 hash-chained to the previous entry.
Modify one entry and the entire chain breaks — tampering is provable.

```python
# Verify log integrity at any time
soul._orchestrator.logger.verify_chain()  # raises LogIntegrityError if tampered
```

---

## Project structure

```
nvion-protocol/
├── README.md                    ← This file
├── QUICKSTART.md                ← 5-minute setup guide
├── LICENSE                      ← MIT License
├── pyproject.toml               ← Package config (PyPI ready)
├── requirements.txt             ← Dependencies
├── .env.example                 ← Config template
│
├── nvion/
│   ├── __init__.py              ← Public API (NSoul class)
│   ├── cli.py                   ← Owner terminal interface
│   └── core/
│       ├── constitution.py      ← L1: AUTH, integrity, dry-run
│       ├── identity.py          ← L2: Agent registry + scope
│       ├── orchestrator.py      ← L3: Command pipeline
│       ├── halt_engine.py       ← Kill-switch (6 conditions)
│       ├── logger.py            ← Hash-chained audit log
│       ├── telegram_reporter.py ← Owner alerts
│       └── exceptions.py        ← Structured error types
│
├── nvion/adapters/
│   ├── base.py                  ← BaseAgentAdapter
│   └── adapters.py              ← CustomAgentAdapter, LangChain, CrewAI, OpenAI, Function
│
├── constitution/
│   ├── VION.md                  ← Constitutional law template
│   └── IDENTITY.md              ← Agent registry template
│
├── examples/
│   ├── demo.py                  ← Live demo — watch it block restricted actions
│   └── govern_agent.py          ← Integration examples for every framework
│
└── tests/
    ├── test_constitution.py     ← 16 tests
    ├── test_halt_engine.py      ← 13 tests
    ├── test_logger_integrity.py ← 8 tests
    └── test_integration.py      ← 13 tests
```

---

## Run the tests

```bash
pytest tests/
# 50 tests — all should pass
```

---

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `VION_AUTH_TOKEN` | ✅ | Owner AUTH secret |
| `TELEGRAM_BOT_TOKEN` | Recommended | Telegram bot for alerts |
| `TELEGRAM_CHAT_ID` | Recommended | Your Telegram chat ID |
| `SOUL_MD_PATH` | ✅ | Path to VION.md |
| `IDENTITY_MD_PATH` | ✅ | Path to IDENTITY.md |
| `LOG_PATH` | ✅ | Path to activity log |
| `DEPLOYMENT_NAME` | Optional | Identifies deployment in logs |
| `COMMAND_EXPIRY_SECONDS` | Optional | Command timeout (default: 300) |
| `DRY_RUN_DEFAULT` | Optional | TRUE enforces dry-run globally |

---

## CLI commands

```
python -m nvion.cli

nataw_bot> dispatch                         interactive command builder
nataw_bot> dispatch <id> <action> [LIVE]    inline dispatch
nataw_bot> status                           system and agent status
nataw_bot> logs                             last 10 activity log entries
nataw_bot> restart                          clear HALT (Owner only)
nataw_bot> exit
```

---

## Reference deployment

Tested in production on **N Nexus** — AI + Web3 ecosystem by Nathan Daniel.
N Nexus is the reference implementation. The protocol works with any agentic system.

---

## Phase roadmap

| Phase | Status | Scope |
|---|---|---|
| Phase 1 | ✅ Current | Open source. Full governance stack. CLI. |
| Phase 2 | Planned | N VION Studio SaaS. Web dashboard. REST API. Onchain enforcement. |

---

*N VION Protocol — constitutional law for AI agents.*
