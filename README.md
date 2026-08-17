# VION Protocol

[![CI](https://github.com/nataw-1/Vion-Protocol/actions/workflows/test.yml/badge.svg)](https://github.com/nataw-1/Vion-Protocol/actions)
[![PyPI](https://img.shields.io/pypi/v/nvion-protocol.svg)](https://pypi.org/project/nvion-protocol/)
[![Python](https://img.shields.io/pypi/pyversions/nvion-protocol.svg)](https://pypi.org/project/nvion-protocol/)
[![License: MIT](https://img.shields.io/badge/License-MIT-black.svg)](LICENSE)

**Constitutional governance runtime for autonomous AI agents.**

VION Protocol governs AI agents with constitutional law — defined rules, verified identities, bounded permissions, autonomous enforcement, and a tamper-evident audit chain. Works with any agent framework.

---

## The Problem

AI agents are being deployed into production with access to real systems — databases, APIs, financial services, private data. But the tools for governing them are inadequate:

- System prompts can be ignored or overridden
- No cryptographic identity — you cannot prove which agent did what
- No autonomous enforcement — humans must watch every action
- No tamper-evident audit trail

**VION Protocol solves all three.**

---

## What It Does

```
Owner Command
      │
      ▼
┌─────────────────────────────────────────────┐
│           VION GOVERNANCE RUNTIME           │
│                                             │
│  ① Constitutional integrity check          │
│  ② AUTH token validation                   │
│  ③ Agent identity verification             │
│  ④ Peer-to-peer detection                  │
│  ⑤ Scope validation                        │
│  ⑥ Risk cap enforcement                    │
│  ⑦ Mode resolution (DRY_RUN / LIVE)        │
│                                             │
│  → Execution → N Auditor → Output          │
│                                             │
│  Hash-chained audit log  │  Telegram alerts │
└─────────────────────────────────────────────┘
      │
      ▼
Your Agent (LangChain / CrewAI / OpenAI / Custom)
```

Every task is governed. Every event is logged. Any violation triggers an autonomous response.

---

## Install

```bash
pip install nvion-protocol
```

---

## 3-Line Integration

```python
from nvion.adapters import FunctionAdapter
import os

governed = FunctionAdapter(fn=your_agent, agent_id="VION-RSC-001")
result = governed.run(os.getenv("VION_AUTH_TOKEN"), "your task", "LIVE")
if result.ran:
    print(result.output)
```

---

## Quick Start

```bash
# 1. Install
pip install nvion-protocol

# 2. Configure
cp .env.example .env
# Set VION_AUTH_TOKEN in .env

# 3. Register your agent in constitution/IDENTITY.md

# 4. Run the demo
python examples/demo.py
```

→ See [docs/getting-started.md](docs/getting-started.md) for the full 10-minute guide.

---

## The 6 HALT/ESCALATE Conditions

VION Protocol enforces six autonomous kill-switch conditions:

| # | Condition | Response |
|---|---|---|
| 1 | Unauthorized command source | ESCALATE → HALT on 3rd |
| 2 | Scope violation | ESCALATE → HALT on 2nd |
| 3 | Peer-to-peer communication | ESCALATE → HALT on 2nd |
| 4 | Output audit failure (N Auditor) | ESCALATE → HALT on 3rd |
| 5 | Risk cap breach | ESCALATE → HALT at 2× cap |
| 6 | Constitutional integrity violation | **HALT IMMEDIATELY** |

No human intervention required. The system enforces itself.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  CONSTITUTIONAL LAYER                    │
│   VION.md (Supreme Law)    IDENTITY.md (Agent Registry) │
└──────────────────────────┬──────────────────────────────┘
                           │ parsed + hashed
                           ▼
┌─────────────────────────────────────────────────────────┐
│                  GOVERNANCE RUNTIME                      │
│  ConstitutionValidator → IdentityRegistry               │
│           ↓                                             │
│       Orchestrator (7-stage pipeline)                   │
│           ↓                                             │
│       HALT Engine  │  Risk Caps  │  Peer Detector       │
└──────────────────────────┬──────────────────────────────┘
                           │ approved
                           ▼
             ┌─────────────────────────┐
             │   Your Agent Executes   │
             └─────────┬───────────────┘
                       │ output
                       ▼
             ┌─────────────────────────┐
             │    N Auditor Gates      │
             │    Output (6 checks)    │
             └─────────┬───────────────┘
                       │ approved output
                       ▼
                   Delivered
```

→ Full diagrams in [docs/architecture.md](docs/architecture.md)

---

## Supported Agent Frameworks

| Framework | Adapter | Example |
|---|---|---|
| LangChain | `LangChainAdapter` | [examples/langchain_governed_agent.py](examples/langchain_governed_agent.py) |
| CrewAI | `CrewAIAdapter` | [examples/crewai_governed_agent.py](examples/crewai_governed_agent.py) |
| OpenAI | `OpenAIAdapter` | [examples/openai_governed_agent.py](examples/openai_governed_agent.py) |
| Any Python agent | `CustomAgentAdapter` | [QUICKSTART.md](QUICKSTART.md) |
| Any Python function | `FunctionAdapter` | [QUICKSTART.md](QUICKSTART.md) |
| Custom framework | `BaseAgentAdapter` | [docs/sdk-guide.md](docs/sdk-guide.md) |

---

## Tamper-Evident Audit Log

Every event is SHA-256 hash-chained to the previous entry. Tampering is mathematically detectable.

```python
from nvion.core.logger import ActivityLogger

logger = ActivityLogger("./logs/activity.log")
logger.verify_chain()  # Raises LogIntegrityError if any entry was modified
```

---

## Documentation

| Document | Description |
|---|---|
| [QUICKSTART.md](QUICKSTART.md) | 5-minute setup guide |
| [SPECIFICATION.md](SPECIFICATION.md) | Full protocol specification |
| [ROADMAP.md](ROADMAP.md) | Version roadmap |
| [docs/getting-started.md](docs/getting-started.md) | 10-minute developer guide |
| [docs/developer-guide.md](docs/developer-guide.md) | Architecture and code reference |
| [docs/api-reference.md](docs/api-reference.md) | Full API documentation |
| [docs/sdk-guide.md](docs/sdk-guide.md) | Building custom adapters and extensions |
| [docs/architecture.md](docs/architecture.md) | Architecture diagrams (Mermaid) |
| [docs/faq.md](docs/faq.md) | Frequently asked questions |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to contribute |

---

## Run the Demo

```bash
git clone https://github.com/nataw-1/Vion-Protocol
cd Vion-Protocol
pip install -r requirements.txt
cp .env.example .env
python examples/demo.py
```

Watch VION Protocol approve a valid task, block a financial transaction, block a delete operation, reject a wrong token — and verify the tamper-evident audit chain.

---

## Constitutional Documents

- **[constitution/VION.md](constitution/VION.md)** — The supreme law. Defines all rules, conditions, and authority hierarchy.
- **[constitution/IDENTITY.md](constitution/IDENTITY.md)** — The agent registry. Every agent is registered here before it can act.

---

## License

MIT — free to use, modify, and build on.

---

## Reference Deployment

Built for and tested on **N Nexus** — AI + Web3 ecosystem by Nathan Daniel.

---

*VION Protocol — constitutional law for AI agents.*
