"""
VION Protocol — LangChain Governed Agent Example

Demonstrates governing a LangChain agent with full constitutional enforcement.
Every task passes through the 7-stage validation pipeline before execution.

Requirements:
    pip install nvion-protocol langchain langchain-openai
"""

import os
from dotenv import load_dotenv

load_dotenv()


def run_example():
    print("=" * 60)
    print("VION Protocol — LangChain Governed Agent")
    print("=" * 60)
    print()

    # ── Setup ────────────────────────────────────────────────────────────────
    # In a real deployment, replace this mock with a real LangChain agent:
    #
    # from langchain_openai import ChatOpenAI
    # from langchain.agents import create_react_agent, AgentExecutor
    # from langchain.tools import DuckDuckGoSearchRun
    #
    # llm = ChatOpenAI(model="gpt-4o")
    # tools = [DuckDuckGoSearchRun()]
    # agent = create_react_agent(llm, tools, prompt)
    # langchain_agent = AgentExecutor(agent=agent, tools=tools)

    class MockLangChainAgent:
        """Simulates a LangChain AgentExecutor for demonstration."""

        def invoke(self, inputs: dict) -> dict:
            task = inputs.get("input", "")
            return {"output": f"[LangChain] Research complete for: '{task}'"}

        def run(self, task: str) -> str:
            return f"[LangChain] Result for: '{task}'"

    langchain_agent = MockLangChainAgent()

    # ── Govern it ────────────────────────────────────────────────────────────
    from nvion.adapters import LangChainAdapter

    governed = LangChainAdapter(
        agent=langchain_agent,
        agent_id="VION-RSC-001",
    )

    token = os.getenv("VION_AUTH_TOKEN", "demo-token")

    # ── Scenario 1: Valid research task ───────────────────────────────────
    print("Scenario 1 — Valid research task")
    print("-" * 40)
    result = governed.run(token, "search recent AI governance papers", "LIVE")
    print(f"  Approved : {result.approved}")
    print(f"  Ran      : {result.ran}")
    if result.ran:
        print(f"  Output   : {result.output}")
    print()

    # ── Scenario 2: Dry-run validation ────────────────────────────────────
    print("Scenario 2 — Dry-run validation (no execution)")
    print("-" * 40)
    result = governed.run(token, "analyze recent transformer architectures", "DRY_RUN")
    print(f"  Approved : {result.approved}")
    print(f"  Dry run  : {result.dry_run}")
    print(f"  Message  : {result.message[:80]}")
    print()

    # ── Scenario 3: Blocked — wrong token ─────────────────────────────────
    print("Scenario 3 — Wrong AUTH token (Condition 1)")
    print("-" * 40)
    result = governed.run("wrong-token", "search papers", "LIVE")
    print(f"  Approved : {result.approved}")
    print(f"  Blocked  : {result.blocked_reason}")
    print()

    print("LangChain example complete.")
    print("Every task passed through VION Protocol's 7-stage governance pipeline.")


if __name__ == "__main__":
    run_example()
