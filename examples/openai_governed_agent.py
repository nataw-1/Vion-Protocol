"""
VION Protocol — OpenAI Governed Agent Example

Demonstrates governing direct OpenAI API calls constitutionally.

Requirements:
    pip install nvion-protocol openai
"""

import os
from dotenv import load_dotenv

load_dotenv()


def run_example():
    print("=" * 60)
    print("VION Protocol — OpenAI Governed Agent")
    print("=" * 60)
    print()

    # ── Mock OpenAI Client ───────────────────────────────────────────────────
    # Replace with real OpenAI client:
    #
    # from openai import OpenAI
    # client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    class MockMessage:
        def __init__(self, content):
            self.content = content

    class MockChoice:
        def __init__(self, content):
            self.message = MockMessage(content)

    class MockResponse:
        def __init__(self, content):
            self.choices = [MockChoice(content)]

    class MockOpenAIClient:
        """Simulates openai.OpenAI() for demonstration."""

        class chat:
            class completions:
                @staticmethod
                def create(model, messages, **kwargs):
                    user_msg = messages[-1]["content"]
                    return MockResponse(f"[GPT-4o] Response to: '{user_msg}'")

    client = MockOpenAIClient()

    # ── Govern it ────────────────────────────────────────────────────────────
    from nvion.adapters import OpenAIAdapter

    governed = OpenAIAdapter(
        client=client,
        agent_id="VION-RSC-001",
        model="gpt-4o",
        system_prompt="You are a constitutional AI research assistant.",
    )

    token = os.getenv("VION_AUTH_TOKEN", "demo-token")

    # ── Scenario 1: Valid query ───────────────────────────────────────────
    print("Scenario 1 — Valid research query")
    print("-" * 40)
    result = governed.run(token, "explain constitutional AI governance", "LIVE")
    print(f"  Approved : {result.approved}")
    print(f"  Ran      : {result.ran}")
    if result.ran:
        print(f"  Output   : {result.output[:80]}")
    print()

    # ── Scenario 2: Dry-run ───────────────────────────────────────────────
    print("Scenario 2 — Dry-run (validate only, no API call)")
    print("-" * 40)
    result = governed.run(token, "summarize VION Protocol architecture", "DRY_RUN")
    print(f"  Approved : {result.approved}")
    print(f"  Dry run  : {result.dry_run}")
    print(f"  Message  : {result.message[:80]}")
    print()

    # ── Scenario 3: Unregistered agent blocked ────────────────────────────
    print("Scenario 3 — Unregistered agent ID (Condition 1)")
    print("-" * 40)
    from nvion.adapters import OpenAIAdapter as OAI
    bad_governed = OAI(client=client, agent_id="VION-GHOST-999", model="gpt-4o")
    result = bad_governed.run(token, "search papers", "LIVE")
    print(f"  Approved : {result.approved}")
    print(f"  Message  : {result.message[:80]}")
    print()

    print("OpenAI example complete.")


if __name__ == "__main__":
    run_example()
