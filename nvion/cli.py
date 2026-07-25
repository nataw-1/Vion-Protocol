"""
N VION Protocol — Owner CLI
The terminal interface for issuing OWNER_COMMANDs to Nataw_bot.
Run: python cli.py
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

load_dotenv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.orchestrator import Orchestrator, OwnerCommand

console = Console()


# ─── DISPLAY HELPERS ──────────────────────────────────────────────────────────

def print_banner():
    console.print(Panel.fit(
        "[bold]N VION Protocol[/bold] — Orchestrator CLI\n"
        "[dim]Phase 1 · Off-Chain · Constitutional Governance for AI Agents[/dim]",
        border_style="dim",
    ))

def print_success(message: str):
    console.print(f"\n[green]✓[/green] {message}\n")

def print_error(message: str):
    console.print(f"\n[red]✗[/red] {message}\n")

def print_warning(message: str):
    console.print(f"\n[yellow]⚠[/yellow] {message}\n")

def print_result(result):
    style = "green" if result.success else "red"
    status = "SUCCESS" if result.success else "FAILED"
    console.print(Panel(
        result.message,
        title=f"[{style}]{status}[/{style}]",
        border_style=style,
    ))

def print_status(status: dict):
    """Display system status in a formatted table."""
    halt_status = "[red]HALTED[/red]" if status["system_halted"] else "[green]ONLINE[/green]"
    console.print(f"\n[bold]System Status:[/bold] {halt_status}")
    console.print(f"[dim]Session: {status['session_id']} · Deployment: {status['deployment']}[/dim]")
    console.print(f"[dim]Telegram: {'enabled' if status['telegram_enabled'] else 'not configured'}[/dim]\n")

    table = Table(box=box.SIMPLE, show_header=True, header_style="bold dim")
    table.add_column("Agent ID", style="dim", width=18)
    table.add_column("Name", width=24)
    table.add_column("Status", width=12)

    for agent in status["active_agents"]:
        status_color = {
            "ACTIVE": "green",
            "SUSPENDED": "yellow",
            "TERMINATED": "red",
        }.get(agent["status"], "white")

        table.add_row(
            agent["id"],
            agent["name"],
            f"[{status_color}]{agent['status']}[/{status_color}]",
        )

    console.print(table)

    counts = status["condition_counts"]
    if any(v > 0 for v in counts.values()):
        console.print("[bold]Condition counts this session:[/bold]")
        for name, count in counts.items():
            if count > 0:
                console.print(f"  [yellow]Condition {name}: {count}[/yellow]")
    console.print()


# ─── COMMAND BUILDERS ─────────────────────────────────────────────────────────

def build_command_interactive(auth_token: str) -> OwnerCommand:
    """Walk the Owner through building a command interactively."""
    console.print("\n[bold]New OWNER_COMMAND[/bold]")

    target = Prompt.ask("  Target agent ID", default="VION-RSC-001")
    action = Prompt.ask("  Action")
    mode   = Prompt.ask("  Mode", choices=["DRY_RUN", "LIVE"], default="DRY_RUN")

    return OwnerCommand(
        auth_token=auth_token,
        target=target,
        action=action,
        mode=mode,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

def build_command_from_args(args: list[str], auth_token: str) -> OwnerCommand:
    """
    Parse a command from CLI arguments.
    Usage: python cli.py dispatch <target> <action> [LIVE]
    """
    if len(args) < 2:
        raise ValueError("Usage: dispatch <target_agent_id> <action> [LIVE]")

    target = args[0]
    action = " ".join(args[1:-1]) if len(args) > 2 and args[-1].upper() in ("LIVE", "DRY_RUN") else " ".join(args[1:])
    mode   = args[-1].upper() if args[-1].upper() in ("LIVE", "DRY_RUN") else "DRY_RUN"

    return OwnerCommand(
        auth_token=auth_token,
        target=target,
        action=action,
        mode=mode,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


# ─── MAIN CLI ─────────────────────────────────────────────────────────────────

def main():
    print_banner()

    # Get AUTH token
    auth_token = os.getenv("VION_AUTH_TOKEN", "")
    if not auth_token:
        print_error("VION_AUTH_TOKEN not set in environment. Check your .env file.")
        sys.exit(1)

    # Boot orchestrator
    console.print("[dim]Starting orchestrator...[/dim]")
    try:
        orchestrator = Orchestrator()
    except FileNotFoundError as e:
        print_error(str(e))
        sys.exit(1)

    print_success("Orchestrator online.")

    # ── COMMAND LOOP ──────────────────────────────────────────────────────────
    console.print("[dim]Commands: dispatch, status, logs, restart, exit[/dim]\n")

    while True:
        try:
            cmd = Prompt.ask("[bold]nataw_bot[/bold]").strip().lower()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Exiting.[/dim]")
            break

        if cmd in ("exit", "quit", "q"):
            console.print("[dim]Goodbye.[/dim]")
            break

        elif cmd == "status":
            status = orchestrator.get_status()
            print_status(status)

        elif cmd.startswith("dispatch"):
            parts = cmd.split(None, 1)
            try:
                if len(parts) == 1:
                    # Interactive mode
                    command = build_command_interactive(auth_token)
                else:
                    # Inline mode: dispatch VION-RSC-001 search recent AI frameworks LIVE
                    args = parts[1].split()
                    command = build_command_from_args(args, auth_token)

                console.print(
                    f"\n[dim]→ Dispatching to {command.target} | "
                    f"{command.action} | {command.mode}[/dim]"
                )
                result = orchestrator.process_command(command)
                print_result(result)

            except ValueError as e:
                print_error(str(e))

        elif cmd == "logs":
            entries = orchestrator.logger.read_recent(10)
            if not entries:
                console.print("[dim]No log entries found.[/dim]\n")
                continue

            table = Table(box=box.SIMPLE, show_header=True, header_style="bold dim")
            table.add_column("Time", style="dim", width=22)
            table.add_column("Event", width=24)
            table.add_column("Details", width=40)

            for entry in entries:
                ts = entry.get("timestamp", "")[:19].replace("T", " ")
                event = entry.get("event_type", "")
                detail = (
                    entry.get("action") or
                    entry.get("reason") or
                    entry.get("message") or
                    ""
                )[:40]

                event_color = "red" if "HALT" in event else "yellow" if "ESCALATE" in event or "REJECT" in event else "dim"
                table.add_row(ts, f"[{event_color}]{event}[/{event_color}]", detail)

            console.print(table)

        elif cmd == "restart":
            console.print("[yellow]Restart clears the HALT state. Owner only.[/yellow]")
            confirm = Prompt.ask("Confirm restart?", choices=["yes", "no"], default="no")
            if confirm == "yes":
                result = orchestrator.restart_after_halt(auth_token)
                if result["success"]:
                    print_success(result["message"])
                else:
                    print_error(result["message"])

        elif cmd == "help":
            console.print(
                "\n[bold]Available commands:[/bold]\n"
                "  [cyan]dispatch[/cyan]          — interactive command builder\n"
                "  [cyan]dispatch[/cyan] [dim]<id> <action> [LIVE][/dim]  — inline dispatch\n"
                "  [cyan]status[/cyan]            — show system and agent status\n"
                "  [cyan]logs[/cyan]              — show last 10 activity log entries\n"
                "  [cyan]restart[/cyan]           — clear HALT state (Owner only)\n"
                "  [cyan]exit[/cyan]              — quit\n"
            )

        elif cmd == "":
            continue

        else:
            print_warning(f"Unknown command: '{cmd}'. Type 'help' for available commands.")


if __name__ == "__main__":
    main()
