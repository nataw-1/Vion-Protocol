"""
N VION Protocol — Integration Examples
Complete working examples for governing different agent systems.

Run this file directly to see N-VION governing a mock agent:
    python examples/govern_agent.py
"""

import os
import sys
from pathlib import Path

# ── Make sure nvion is importable from this examples folder ──────────────────
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from nvion.adapters import CustomAgentAdapter, FunctionAdapter, BaseAgentAdapter


# =============================================================================
# EXAMPLE 1 — Govern a CUSTOM agent (OpenClaw, Hermes, or any custom agent)
# This is the pattern to use when you have your own agent class
# =============================================================================

class MockOpenClawAgent:
    """
    Simulates what OpenClaw or Hermes or any custom agent looks like.
    Replace this with your real agent import.
    """
    def execute(self, prompt: str) -> str:
        return f"[OpenClaw Result] Processed: '{prompt}' — task complete."


def example_openclaw_hermes():
    print("\n" + "="*60)
    print("EXAMPLE 1 — Governing OpenClaw / Hermes / Custom Agent")
    print("="*60)

    # Your real agent
    openclaw_agent = MockOpenClawAgent()

    # Wrap it with N-VION governance
    # call_method="execute" means N-VION will call agent.execute(action)
    # call_kwarg="prompt" means it passes action as: agent.execute(prompt=action)
    governed = CustomAgentAdapter(
        agent=openclaw_agent,
        agent_id="VION-RSC-001",         # Must match IDENTITY.md
        call_method="execute",
        call_kwarg="prompt",
    )

    auth_token = os.getenv("VION_AUTH_TOKEN", "")

    # ── DRY RUN first (always safe to test) ──────────────────────────────────
    print("\n→ Dry run test:")
    result = governed.run(
        auth_token=auth_token,
        action="search recent AI governance frameworks",
        mode="DRY_RUN",
    )
    print(f"  Approved : {result.approved}")
    print(f"  Message  : {result.message}")

    # ── LIVE run ──────────────────────────────────────────────────────────────
    print("\n→ Live run:")
    result = governed.run(
        auth_token=auth_token,
        action="search recent AI governance frameworks",
        mode="LIVE",
    )
    print(f"  Approved : {result.approved}")
    print(f"  Ran      : {result.ran}")
    print(f"  Output   : {result.output}")

    # ── Test what happens with a WRONG auth token ─────────────────────────────
    print("\n→ Wrong auth token test:")
    result = governed.run(
        auth_token="wrong-token-123",
        action="search something",
        mode="LIVE",
    )
    print(f"  Approved : {result.approved}")
    print(f"  Blocked  : {result.blocked_reason}")


# =============================================================================
# EXAMPLE 2 — Govern any plain Python function as an agent
# Simplest possible integration
# =============================================================================

def example_function_agent():
    print("\n" + "="*60)
    print("EXAMPLE 2 — Governing a plain Python function")
    print("="*60)

    # Any function becomes a governed agent
    def my_research_agent(task: str) -> str:
        # Replace with your real agent logic
        return f"Research complete for: {task}"

    governed = FunctionAdapter(
        fn=my_research_agent,
        agent_id="VION-RSC-001",
    )

    result = governed.run(
        auth_token=os.getenv("VION_AUTH_TOKEN", ""),
        action="find latest papers on AI safety",
        mode="LIVE",
    )

    print(f"\n  Approved : {result.approved}")
    print(f"  Output   : {result.output}")


# =============================================================================
# EXAMPLE 3 — Build your own adapter for any framework
# The pattern for LangChain, CrewAI, AutoGen, or anything custom
# =============================================================================

def example_custom_adapter():
    print("\n" + "="*60)
    print("EXAMPLE 3 — Building a custom adapter for your framework")
    print("="*60)

    class MyHermesAdapter(BaseAgentAdapter):
        """
        Replace this with your real Hermes agent import and call.
        This pattern works for ANY agent framework.
        """

        def __init__(self, agent_id: str):
            super().__init__(agent_id=agent_id)
            # Initialize your real agent here
            # self.hermes = HermesAgent(model="hermes-3", ...)
            self.hermes = None  # placeholder

        def _run_agent(self, action: str, **kwargs) -> str:
            # Replace this line with your real agent call:
            # return self.hermes.chat(action)
            return f"[Hermes Mock] Task completed: {action}"

    adapter = MyHermesAdapter(agent_id="VION-RSC-001")

    result = adapter.run(
        auth_token=os.getenv("VION_AUTH_TOKEN", ""),
        action="analyze this dataset",
        mode="LIVE",
    )

    print(f"\n  Approved : {result.approved}")
    print(f"  Output   : {result.output}")
    print(f"  Message  : {result.message}")


# =============================================================================
# EXAMPLE 4 — Check system status and agent registry
# =============================================================================

def example_status_check():
    print("\n" + "="*60)
    print("EXAMPLE 4 — Checking N-VION system status")
    print("="*60)

    # Any adapter gives you access to system status
    def dummy(task): return task
    adapter = FunctionAdapter(fn=dummy, agent_id="VION-RSC-001")

    status = adapter.get_status()
    print(f"\n  System halted    : {status['system_halted']}")
    print(f"  Session ID       : {status['session_id']}")
    print(f"  Deployment       : {status['deployment']}")
    print(f"  Telegram enabled : {status['telegram_enabled']}")
    print(f"  Registered agents:")
    for agent in status["active_agents"]:
        print(f"    {agent['id']} — {agent['name']} [{agent['status']}]")


# =============================================================================
# RUN ALL EXAMPLES
# =============================================================================

if __name__ == "__main__":
    print("\nN VION Protocol — Integration Examples")
    print("Testing governance of external agent systems\n")

    try:
        example_openclaw_hermes()
        example_function_agent()
        example_custom_adapter()
        example_status_check()
    except FileNotFoundError as e:
        print(f"\n[Setup Error] {e}")
        print("Make sure you have:")
        print("  1. constitution/VION.md in place")
        print("  2. constitution/IDENTITY.md in place")
        print("  3. .env configured with VION_AUTH_TOKEN")
    except Exception as e:
        print(f"\n[Error] {e}")

    print("\n" + "="*60)
    print("Done. Check logs/activity.log for the full audit trail.")
    print("="*60 + "\n")
