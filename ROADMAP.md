# N VION Protocol — Roadmap

Constitutional governance runtime for autonomous AI agents.

---

## v1.0.0 — Core Constitutional Runtime ✅ Current

The foundation. Everything needed to govern an AI agent with constitutional law.

- ✅ VION.md — constitutional law document
- ✅ IDENTITY.md — agent identity registry
- ✅ AUTH token validation (constant-time, replay protection)
- ✅ Orchestrator command pipeline (7-step validation)
- ✅ HALT Engine — all 6 conditions wired and firing
- ✅ N Auditor — output gating (Condition 4)
- ✅ Risk cap evaluator (Condition 5)
- ✅ Peer-to-peer detection (Condition 3)
- ✅ Hash-chained tamper-evident audit log
- ✅ Per-command constitutional integrity check (Condition 6)
- ✅ Telegram real-time alerts
- ✅ 5 agent adapters (Function, Custom, LangChain, CrewAI, OpenAI)
- ✅ Suspension persistence (governance.state)
- ✅ Owner CLI
- ✅ 50 tests, GitHub Actions CI

---

## v1.1.0 — Persistent Governance State

- Durable HALT state and condition counts survive restarts
- GovernanceStateStore abstraction (file-backed, Redis-ready)
- Agent lifecycle API — suspend, reactivate, terminate without editing markdown
- Constitutional amendment workflow with version bump and reload

---

## v1.2.0 — Policy Engine

- Structured permission schema replacing plain-text permission strings
- YAML/JSON permission blocks in IDENTITY.md — machine-enforceable
- Tool-level governance hooks for LangChain and CrewAI tool calls
- Resource-level ACLs per agent

---

## v1.3.0 — Session Governance

- Session context tracking per agent run
- Max actions per session enforced at orchestrator level
- Time-bounded authority — commands expire after defined window
- Session audit reports — exportable and signable

---

## v1.4.0 — Observability and Compliance

- OpenTelemetry spans on the dispatch pipeline
- Log redaction and retention policy configuration
- Exportable audit reports (PDF, JSON, CSV)
- SIEM integration hooks
- Full threat model documentation

---

## v2.0.0 — N VION Studio (SaaS)

- Visual constitution editor — no more editing VION.md by hand
- Agent registry UI — no more editing IDENTITY.md by hand
- Live activity feed — real-time governed event stream
- HALT and ESCALATE panel with one-click Owner restart
- REST API — govern agents from any language via HTTP
- Clerk authentication and team access
- Stripe billing (Free / Pro $29/mo / Team $99/mo / Enterprise)
- Layer 5 onchain enforcement — smart contracts encode VION.md rules

---

## Contributing

Issues, pull requests, and feedback are welcome.
See [QUICKSTART.md](./QUICKSTART.md) to get started.

---

*N VION Protocol — constitutional law for AI agents.*
