"""
N VION Protocol — Ready-Made Adapters
Pre-built adapters for popular agent frameworks.

Pick the one that matches your agent system and extend it.
If your framework isn't here, extend BaseAgentAdapter directly.
"""

from typing import Any, Optional

from ..core.orchestrator import Orchestrator
from .base import BaseAgentAdapter

# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM / GENERIC ADAPTER
# Use this for OpenClaw, Hermes, or any custom Python agent
# ─────────────────────────────────────────────────────────────────────────────

class CustomAgentAdapter(BaseAgentAdapter):
    """
    Adapter for any custom Python agent — OpenClaw, Hermes, or your own.

    Your agent just needs to be callable with a string prompt/action.

    Usage:
        # Your agent can use any of these call styles:

        # Style A — agent.run(action)
        adapter = CustomAgentAdapter(
            agent=your_agent,
            agent_id="VION-RSC-001",
            call_method="run",
        )

        # Style B — agent.execute(prompt=action)
        adapter = CustomAgentAdapter(
            agent=your_agent,
            agent_id="VION-RSC-001",
            call_method="execute",
            call_kwarg="prompt",
        )

        # Style C — agent(action) direct callable
        adapter = CustomAgentAdapter(
            agent=your_agent,
            agent_id="VION-RSC-001",
            call_method="__call__",
        )

        # Then govern it:
        import os
        result = adapter.run(
            auth_token=os.getenv("VION_AUTH_TOKEN"),
            action="your task here",
            mode="LIVE",
        )
        if result.ran:
            print(result.output)
    """

    def __init__(
        self,
        agent: Any,
        agent_id: str,
        call_method: str = "run",
        call_kwarg: Optional[str] = None,
        orchestrator: Optional[Orchestrator] = None,
    ):
        """
        Parameters:
            agent        — Your agent object
            agent_id     — SOUL agent ID (must match IDENTITY.md)
            call_method  — The method name to call on your agent
                           e.g. "run", "execute", "invoke", "__call__"
            call_kwarg   — If your agent takes a keyword arg instead of positional
                           e.g. "prompt", "task", "query", "input"
            orchestrator — Optional existing Orchestrator instance
        """
        super().__init__(agent_id=agent_id, orchestrator=orchestrator)
        self._agent = agent
        self._call_method = call_method
        self._call_kwarg = call_kwarg

    def _run_agent(self, action: str, **kwargs) -> Any:
        method = getattr(self._agent, self._call_method)
        if self._call_method == "__call__":
            return self._agent(action, **kwargs)
        if self._call_kwarg:
            return method(**{self._call_kwarg: action}, **kwargs)
        return method(action, **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# LANGCHAIN ADAPTER
# ─────────────────────────────────────────────────────────────────────────────

class LangChainAdapter(BaseAgentAdapter):
    """
    Adapter for LangChain agents and chains.

    Usage:
        from langchain.agents import initialize_agent
        from nvion.adapters import LangChainAdapter

        langchain_agent = initialize_agent(tools, llm, ...)

        adapter = LangChainAdapter(
            agent=langchain_agent,
            agent_id="VION-RSC-001",
        )

        result = adapter.run(
            auth_token=os.getenv("VION_AUTH_TOKEN"),
            action="search recent AI papers",
            mode="LIVE",
        )
    """

    def __init__(
        self,
        agent: Any,
        agent_id: str,
        orchestrator: Optional[Orchestrator] = None,
    ):
        super().__init__(agent_id=agent_id, orchestrator=orchestrator)
        self._agent = agent

    def _run_agent(self, action: str, **kwargs) -> Any:
        # LangChain agents use .run() or .invoke()
        if hasattr(self._agent, "invoke"):
            return self._agent.invoke({"input": action}, **kwargs)
        return self._agent.run(action, **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# CREWAI ADAPTER
# ─────────────────────────────────────────────────────────────────────────────

class CrewAIAdapter(BaseAgentAdapter):
    """
    Adapter for CrewAI crews.

    Usage:
        from crewai import Crew
        from nvion.adapters import CrewAIAdapter

        my_crew = Crew(agents=[...], tasks=[...])

        adapter = CrewAIAdapter(
            crew=my_crew,
            agent_id="VION-EXC-001",
        )

        result = adapter.run(
            auth_token=os.getenv("VION_AUTH_TOKEN"),
            action="research and summarize AI governance trends",
            mode="LIVE",
        )
    """

    def __init__(
        self,
        crew: Any,
        agent_id: str,
        orchestrator: Optional[Orchestrator] = None,
    ):
        super().__init__(agent_id=agent_id, orchestrator=orchestrator)
        self._crew = crew

    def _run_agent(self, action: str, **kwargs) -> Any:
        return self._crew.kickoff(inputs={"task": action, **kwargs})


# ─────────────────────────────────────────────────────────────────────────────
# OPENAI ADAPTER
# ─────────────────────────────────────────────────────────────────────────────

class OpenAIAdapter(BaseAgentAdapter):
    """
    Adapter for direct OpenAI API calls.

    Usage:
        from openai import OpenAI
        from nvion.adapters import OpenAIAdapter

        client = OpenAI(api_key="your-key")

        adapter = OpenAIAdapter(
            client=client,
            agent_id="VION-RSC-001",
            model="gpt-4o",
            system_prompt="You are a research assistant.",
        )

        result = adapter.run(
            auth_token=os.getenv("VION_AUTH_TOKEN"),
            action="summarize AI governance frameworks",
            mode="LIVE",
        )
    """

    def __init__(
        self,
        client: Any,
        agent_id: str,
        model: str = "gpt-4o",
        system_prompt: str = "You are a helpful AI assistant.",
        orchestrator: Optional[Orchestrator] = None,
    ):
        super().__init__(agent_id=agent_id, orchestrator=orchestrator)
        self._client = client
        self._model = model
        self._system_prompt = system_prompt

    def _run_agent(self, action: str, **kwargs) -> Any:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": self._system_prompt},
                {"role": "user", "content": action},
            ],
            **kwargs,
        )
        return response.choices[0].message.content


# ─────────────────────────────────────────────────────────────────────────────
# FUNCTION ADAPTER
# Simplest possible adapter — wrap any Python function as a governed agent
# ─────────────────────────────────────────────────────────────────────────────

class FunctionAdapter(BaseAgentAdapter):
    """
    Wrap any Python function as a governed N-VION agent.
    The simplest way to add governance to any callable.

    Usage:
        def my_agent_function(task: str) -> str:
            # your logic here
            return f"Result for: {task}"

        adapter = FunctionAdapter(
            fn=my_agent_function,
            agent_id="VION-RSC-001",
        )

        result = adapter.run(
            auth_token=os.getenv("VION_AUTH_TOKEN"),
            action="do something",
            mode="LIVE",
        )
    """

    def __init__(
        self,
        fn: Any,
        agent_id: str,
        orchestrator: Optional[Orchestrator] = None,
    ):
        super().__init__(agent_id=agent_id, orchestrator=orchestrator)
        self._fn = fn

    def _run_agent(self, action: str, **kwargs) -> Any:
        return self._fn(action, **kwargs)
