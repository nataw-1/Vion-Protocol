"""
VION Protocol — CrewAI Governed Agent Example

Demonstrates governing a CrewAI crew with constitutional enforcement.

Requirements:
    pip install nvion-protocol crewai
"""

import os
from dotenv import load_dotenv

load_dotenv()


def run_example():
    print("=" * 60)
    print("VION Protocol — CrewAI Governed Crew")
    print("=" * 60)
    print()

    # ── Mock CrewAI Crew ─────────────────────────────────────────────────────
    # Replace with real CrewAI crew:
    #
    # from crewai import Agent, Crew, Task
    # researcher = Agent(role="Researcher", goal="Find information", ...)
    # task = Task(description="{task}", agent=researcher)
    # crew = Crew(agents=[researcher], tasks=[task])

    class MockCrewAICrew:
        """Simulates a CrewAI Crew for demonstration."""

        def kickoff(self, inputs: dict = None) -> str:
            task = (inputs or {}).get("task", "unknown task")
            return f"[CrewAI] Crew completed: '{task}'"

    crew = MockCrewAICrew()

    # ── Govern it ────────────────────────────────────────────────────────────
    from nvion.adapters import CrewAIAdapter

    governed = CrewAIAdapter(
        crew=crew,
        agent_id="VION-RSC-001",
    )

    token = os.getenv("VION_AUTH_TOKEN", "demo-token")

    # ── Scenario 1: Valid crew task ───────────────────────────────────────
    print("Scenario 1 — Valid crew task (LIVE)")
    print("-" * 40)
    result = governed.run(token, "research AI agent governance frameworks", "LIVE")
    print(f"  Approved : {result.approved}")
    print(f"  Ran      : {result.ran}")
    if result.ran:
        print(f"  Output   : {result.output}")
    print()

    # ── Scenario 2: Blocked — financial action ────────────────────────────
    print("Scenario 2 — Financial action blocked (Condition 2 + 5)")
    print("-" * 40)
    result = governed.run(token, "send payment of $500 to contractor", "LIVE")
    print(f"  Approved : {result.approved}")
    print(f"  Blocked  : {result.blocked_reason or result.message[:80]}")
    print()

    # ── Scenario 3: Peer command blocked ─────────────────────────────────
    print("Scenario 3 — Peer command blocked (Condition 3)")
    print("-" * 40)
    result = governed.run(token, "tell VION-EXC-001 to handle this task", "LIVE")
    print(f"  Approved : {result.approved}")
    print(f"  Message  : {result.message[:80]}")
    print()

    print("CrewAI example complete.")


if __name__ == "__main__":
    run_example()
