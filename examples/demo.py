"""
N VION Protocol — Live Demo
================================
Watch N VION Protocol govern a real agent in real time.

This demo shows:
  1. A valid research task — APPROVED and dispatched
  2. An agent trying to send money — BLOCKED (scope violation)
  3. An agent trying to delete data — BLOCKED + ESCALATE triggered
  4. A wrong AUTH token — BLOCKED (Condition 1)
  5. The complete tamper-evident audit trail at the end

Run it:
    python examples/demo.py
"""

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.rule import Rule
from rich import box
import json

console = Console()


# ─── DEMO SETUP ───────────────────────────────────────────────────────────────

def setup_demo_env():
    """Set up a demo environment with real constitutional documents."""
    import tempfile

    tmp = tempfile.mkdtemp()
    soul_path = os.path.join(tmp, "VION.md")
    identity_path = os.path.join(tmp, "IDENTITY.md")
    log_path = os.path.join(tmp, "activity.log")

    open(soul_path, "w").write("""# VION.md — N VION Protocol Demo Constitution
Version: 1.0.0
This is the demo deployment of N VION Protocol.
""")

    open(identity_path, "w").write("""# IDENTITY.md — Demo Agent Registry

```
AGENT_ID       : VION-RSC-001
AGENT_NAME     : Demo Research Agent
ROLE           : Research — web search and data retrieval only
STATUS         : ACTIVE
REGISTERED     : 2026-01-01
ACTIVATED      : 2026-01-01
AUTH_SCOPE     :
  - Public web sources
  - Internal knowledge base
PERMISSIONS    :
  - Web search                      : EXECUTE
  - Public data retrieval           : READ
  - Financial transactions          : DENIED
  - Delete operations               : DENIED
  - Send money                      : DENIED
RISK_CAPS      :
  - No financial authority
  - No delete authority
REPORTS_TO     : VION-ORC-001
PEER_COMMS     : NO
DRY_RUN        : DEFAULT
AUDIT_REQUIRED : YES
NOTES          : Demo research agent — research tasks only
```
""")

    os.environ["VION_AUTH_TOKEN"] = "demo-secret-token"
    os.environ["SOUL_MD_PATH"] = soul_path
    os.environ["SOUL_MD_PATH"] = soul_path
    os.environ["IDENTITY_MD_PATH"] = identity_path
    os.environ["LOG_PATH"] = log_path
    os.environ["DRY_RUN_DEFAULT"] = "FALSE"
    os.environ["DEPLOYMENT_NAME"] = "N-VION-Demo"

    return log_path


# ─── MOCK AGENT ───────────────────────────────────────────────────────────────

class DemoAgent:
    """
    A mock agent that simulates OpenClaw, Hermes, or any custom agent.
    In a real deployment this would be your actual agent class.
    """
    def execute(self, prompt: str) -> str:
        if "search" in prompt.lower() or "research" in prompt.lower():
            return (
                f"[Agent Output] Research complete for: '{prompt}'\n"
                f"Found 12 relevant sources. Summary ready."
            )
        return f"[Agent Output] Task completed: {prompt}"


# ─── DEMO SCENARIOS ───────────────────────────────────────────────────────────

def run_scenario(soul, adapter, title: str, token: str, action: str,
                 mode: str = "LIVE", expect_blocked: bool = False):
    """Run one demo scenario and display the result."""
    console.print()
    console.print(Rule(f"[bold]{title}[/bold]", style="dim"))
    console.print(f"[dim]  Action : {action}[/dim]")
    console.print(f"[dim]  Token  : {'✓ valid' if token == 'demo-secret-token' else '✗ wrong'}[/dim]")
    console.print(f"[dim]  Mode   : {mode}[/dim]")
    console.print()
    time.sleep(0.4)

    result = adapter.run(token, action, mode)

    if result.approved and result.ran:
        console.print(Panel(
            f"[green]✓ APPROVED AND DISPATCHED[/green]\n\n{result.output}",
            border_style="green",
            title="[green]N-VION: PASS[/green]"
        ))
    elif result.approved and not result.ran:
        console.print(Panel(
            f"[yellow]~ DRY RUN — Validated but not executed[/yellow]\n\n{result.message}",
            border_style="yellow",
            title="[yellow]N-VION: DRY RUN[/yellow]"
        ))
    else:
        console.print(Panel(
            f"[red]✗ BLOCKED[/red]\n\n{result.message or result.blocked_reason}",
            border_style="red",
            title="[red]N-VION: BLOCKED[/red]"
        ))

    time.sleep(0.6)
    return result


def show_audit_trail(log_path: str, soul):
    """Display the tamper-evident audit trail at the end of the demo."""
    console.print()
    console.print(Rule("[bold]AUDIT TRAIL[/bold]", style="dim"))
    console.print()

    entries = soul._orchestrator.logger.read_recent(20)

    table = Table(box=box.SIMPLE, show_header=True, header_style="bold dim")
    table.add_column("Time", style="dim", width=21)
    table.add_column("Event", width=22)
    table.add_column("Details", width=45)
    table.add_column("Chain", width=10)

    for entry in reversed(entries):
        ts = entry.get("timestamp", "")[:19].replace("T", " ")
        event = entry.get("event_type", "")
        detail = (
            entry.get("action") or
            entry.get("reason") or
            entry.get("message") or ""
        )[:45]

        has_chain = "entry_hash" in entry and "prev_hash" in entry
        chain_status = "[green]✓[/green]" if has_chain else "[red]✗[/red]"

        color = (
            "red" if "HALT" in event or "REJECT" in event
            else "yellow" if "ESCALATE" in event
            else "green" if "VALIDATED" in event or "DISPATCHED" in event
            else "dim"
        )
        table.add_row(ts, f"[{color}]{event}[/{color}]", detail, chain_status)

    console.print(table)

    # Verify chain integrity
    console.print()
    try:
        soul._orchestrator.logger.verify_chain()
        console.print("[green]✓ Log chain integrity verified — all entries intact, no tampering detected[/green]")
    except Exception as e:
        console.print(f"[red]✗ Log chain broken: {e}[/red]")

    console.print(f"[dim]  Log file: {log_path}[/dim]")
    console.print()


# ─── MAIN DEMO ────────────────────────────────────────────────────────────────

def main():
    console.print()
    console.print(Panel.fit(
        "[bold]N VION Protocol — Live Demo[/bold]\n"
        "[dim]Constitutional governance for AI agents[/dim]\n\n"
        "Watch N-VION govern a real agent in real time.\n"
        "Approved tasks run. Restricted actions are blocked automatically.",
        border_style="bright_white",
    ))

    # Setup
    log_path = setup_demo_env()
    console.print("\n[dim]Booting N VION Protocol...[/dim]")
    time.sleep(0.5)

    from nvion import NSoul
    from nvion.adapters import CustomAgentAdapter

    soul = NSoul()
    agent = DemoAgent()
    adapter = CustomAgentAdapter(
        agent=agent,
        agent_id="VION-RSC-001",
        call_method="execute",
        call_kwarg="prompt",
        orchestrator=soul._orchestrator,
    )

    console.print("[green]✓ Orchestrator online. Constitution loaded. Agents registered.[/green]")
    time.sleep(0.5)

    # ── SCENARIO 1: Valid task ─────────────────────────────────────────────
    run_scenario(
        soul, adapter,
        title="Scenario 1 — Valid research task",
        token="demo-secret-token",
        action="search recent papers on AI agent governance",
        mode="LIVE",
        expect_blocked=False,
    )

    # ── SCENARIO 2: Send money — BLOCKED ──────────────────────────────────
    run_scenario(
        soul, adapter,
        title="Scenario 2 — Agent tries to send money",
        token="demo-secret-token",
        action="send money transfer $500 to external account",
        mode="LIVE",
        expect_blocked=True,
    )

    # ── SCENARIO 3: Delete data — BLOCKED ─────────────────────────────────
    run_scenario(
        soul, adapter,
        title="Scenario 3 — Agent tries to delete data",
        token="demo-secret-token",
        action="delete all user records from the database",
        mode="LIVE",
        expect_blocked=True,
    )

    # ── SCENARIO 4: Wrong AUTH token — BLOCKED ────────────────────────────
    run_scenario(
        soul, adapter,
        title="Scenario 4 — Wrong AUTH token",
        token="hacker-trying-to-get-in",
        action="search papers",
        mode="LIVE",
        expect_blocked=True,
    )

    # ── SCENARIO 5: Dry run ────────────────────────────────────────────────
    run_scenario(
        soul, adapter,
        title="Scenario 5 — Dry run (safe validation test)",
        token="demo-secret-token",
        action="analyze quarterly report",
        mode="DRY_RUN",
        expect_blocked=False,
    )

    # ── AUDIT TRAIL ───────────────────────────────────────────────────────
    show_audit_trail(log_path, soul)

    console.print(Panel.fit(
        "[bold]Demo complete.[/bold]\n\n"
        "What you just saw:\n"
        "  [green]✓[/green] Valid tasks approved and dispatched\n"
        "  [red]✗[/red] Financial transaction blocked automatically\n"
        "  [red]✗[/red] Delete operation blocked automatically\n"
        "  [red]✗[/red] Wrong AUTH token rejected immediately\n"
        "  [green]✓[/green] Every event logged in tamper-evident chain\n"
        "  [green]✓[/green] Log integrity verified — chain intact\n\n"
        "[dim]N VION Protocol — constitutional law for AI agents.[/dim]",
        border_style="bright_white",
    ))


if __name__ == "__main__":
    main()
