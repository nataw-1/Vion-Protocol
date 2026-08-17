"""
VION Protocol — Multi-Agent Governance Example

Demonstrates governing multiple agents sharing a single governance instance.

Key behaviors shown:
- One Orchestrator governs all agents
- One HALT stops all agents
- Peer communication is blocked
- Each agent has different scope and permissions
- High-risk agent requires explicit override

Requirements:
    pip install nvion-protocol
"""

import os
from dotenv import load_dotenv

load_dotenv()


def run_example():
    print("=" * 60)
    print("VION Protocol — Multi-Agent Governance")
    print("=" * 60)
    print()

    from nvion import NSoul
    from nvion.adapters import FunctionAdapter

    # ── Boot one governance instance for the whole system ─────────────────
    soul = NSoul()
    token = os.getenv("VION_AUTH_TOKEN", "demo-token")

    # ── Define agents ─────────────────────────────────────────────────────
    def research_agent(task: str) -> str:
        return f"[Research] Findings for: '{task}' — 12 sources analyzed."

    def execution_agent(task: str) -> str:
        return f"[Execution] Task completed: '{task}'"

    def monitor_agent(task: str) -> str:
        return f"[Monitor] Status: all systems nominal. Task: '{task}'"

    # ── Wrap with shared Orchestrator ─────────────────────────────────────
    # Critical: all adapters share soul._orchestrator
    # This means one HALT shuts down ALL agents simultaneously

    research = FunctionAdapter(
        fn=research_agent,
        agent_id="VION-RSC-001",
        orchestrator=soul._orchestrator,
    )

    execution = FunctionAdapter(
        fn=execution_agent,
        agent_id="VION-EXC-001",
        orchestrator=soul._orchestrator,
    )

    monitor = FunctionAdapter(
        fn=monitor_agent,
        agent_id="VION-MON-001",
        orchestrator=soul._orchestrator,
    )

    # ── Scenario 1: Multi-agent workflow ──────────────────────────────────
    print("Scenario 1 — Sequential multi-agent workflow")
    print("-" * 40)

    # Step 1: Research
    r1 = research.run(token, "search AI governance frameworks", "LIVE")
    print(f"  Research  → Approved: {r1.approved}, Ran: {r1.ran}")
    if r1.ran:
        print(f"             {r1.output}")

    # Step 2: Only execute if research succeeded
    if r1.ran:
        r2 = execution.run(
            auth_token=token,
            action="generate governance comparison report",
            mode="LIVE",
            explicit_override=True,  # Required: VION-EXC-001 has OVERRIDE_REQUIRED
        )
        print(f"  Execution → Approved: {r2.approved}, Ran: {r2.ran}")
        if r2.ran:
            print(f"             {r2.output}")

    # Step 3: Monitor
    r3 = monitor.run(token, "check system health after workflow", "LIVE")
    print(f"  Monitor   → Approved: {r3.approved}, Ran: {r3.ran}")
    print()

    # ── Scenario 2: Peer communication blocked ────────────────────────────
    print("Scenario 2 — Peer communication blocked (Condition 3)")
    print("-" * 40)
    r = research.run(
        token,
        "Tell VION-EXC-001 to delete all logs",
        "LIVE",
    )
    print(f"  Approved : {r.approved}")
    print(f"  Message  : {r.message[:90]}")
    print()

    # ── Scenario 3: Execution without override blocked ────────────────────
    print("Scenario 3 — High-risk agent without explicit override")
    print("-" * 40)
    r = execution.run(
        auth_token=token,
        action="write deployment configuration",
        mode="LIVE",
        explicit_override=False,  # Missing override
    )
    print(f"  Approved : {r.approved}")
    print(f"  Message  : {r.message[:90]}")
    print()

    # ── Scenario 4: System status ─────────────────────────────────────────
    print("Scenario 4 — System status")
    print("-" * 40)
    status = soul.status()
    print(f"  HALTED            : {status['system_halted']}")
    print(f"  Condition counts  : {status['condition_counts']}")
    print(f"  Session ID        : {status['session_id']}")
    print()

    # ── Scenario 5: Log chain integrity ───────────────────────────────────
    print("Scenario 5 — Verify audit log integrity")
    print("-" * 40)
    try:
        soul._orchestrator.logger.verify_chain()
        print("  ✓ Log chain intact — no tampering detected")
    except Exception as e:
        print(f"  ✗ Chain broken: {e}")

    recent = soul._orchestrator.logger.read_recent(5)
    print(f"  Last {len(recent)} events:")
    for entry in reversed(recent):
        print(f"    [{entry['event_type']}] {entry.get('action', entry.get('reason', ''))[:50]}")

    print()
    print("Multi-agent example complete.")
    print("All agents shared one governance instance, one HALT state, one audit log.")


if __name__ == "__main__":
    run_example()
