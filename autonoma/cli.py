from __future__ import annotations
import sys
import json
import time
import argparse
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from autonoma.core.agent import AutonomousWorker
from autonoma.core.models import StepTrace, TaskStatus
from autonoma.environment.generator import seed_environment, init_database
from autonoma.config import settings

console = Console()

def print_banner():
    banner_text = Text()
    banner_text.append("⚡ AUTONOMA ", style="bold cyan")
    banner_text.append("| Autonomous AI Task Worker\n", style="bold white")
    banner_text.append("Goal-Driven Planning • ReAct Loop • Self-Verification • Safety Guardrails", style="dim")
    console.print(Panel(banner_text, border_style="cyan", box=box.ROUNDED))

def render_step_trace(trace: StepTrace):
    step_num = trace.step_number
    milestone = trace.milestone_title or "General Execution"
    
    # Thought Box
    console.print(f"\n[bold cyan]▶ STEP {step_num}[/bold cyan] [dim]({milestone})[/dim]")
    console.print(f"[bold yellow]🧠 THOUGHT:[/bold yellow] {trace.thought}")

    # Action
    params_str = json.dumps(trace.action.parameters, indent=2)
    console.print(f"[bold blue]⚡ ACTION:[/bold blue] [green]{trace.action.tool_name}[/green]")
    if len(params_str) < 120:
        console.print(f"   [dim]{params_str}[/dim]")
    else:
        console.print(f"   [dim]{params_str[:120]}...[/dim]")

    # Observation
    if trace.observation:
        obs = trace.observation
        status_color = "green" if obs.status == "success" else "red"
        status_tag = f"[{status_color}]● {obs.status.upper()}[/{status_color}]"
        
        obs_preview = ""
        if obs.error_message:
            obs_preview = f"[bold red]Error: {obs.error_message}[/bold red]"
        elif isinstance(obs.data, dict):
            keys = list(obs.data.keys())
            obs_preview = f"Keys: {keys} | Preview: {str(obs.data)[:140]}..."
        else:
            obs_preview = str(obs.data)[:140]

        console.print(f"[bold magenta]👁️  OBSERVATION ({obs.elapsed_ms:.1f}ms):[/bold magenta] {status_tag} {obs_preview}")

    if trace.reflection:
        console.print(f"[bold green]✨ REFLECTION:[/bold green] [italic]{trace.reflection}[/italic]")

def render_completion_report(bundle):
    console.print("\n")
    status_style = "bold green" if bundle.status == TaskStatus.COMPLETED else "bold red"
    
    table = Table(title="📋 TASK COMPLETION CERTIFICATE & EVIDENCE BUNDLE", box=box.ROUNDED, style="cyan")
    table.add_column("Attribute", style="bold white", width=22)
    table.add_column("Value", style="cyan")

    table.add_row("Task ID", bundle.task_id)
    table.add_row("Status", f"[{status_style}]{bundle.status.value.upper()}[/{status_style}]")
    table.add_row("Proof Receipt ID", f"[bold yellow]{bundle.receipt_id}[/bold yellow]")
    table.add_row("Total Steps", str(bundle.total_steps))
    table.add_row("Retries Attempted", str(bundle.retries_attempted))
    table.add_row("Execution Time", f"{bundle.completed_at - bundle.started_at:.2f} seconds")
    
    inv = bundle.extracted_entities.get("extracted_invoice", {})
    if inv:
        table.add_row("Extracted Vendor", str(inv.get("vendor")))
        table.add_row("Invoice Number", str(inv.get("invoice_number")))
        table.add_row("Extracted Amount", f"${float(inv.get('amount', 0)):,.2f}")
        table.add_row("Extracted Due Date", str(inv.get("due_date")))

    console.print(table)

    # Verifications Table
    if bundle.verifications:
        v_table = Table(title="🔍 INDEPENDENT VERIFICATION CHECKS", box=box.SIMPLE_HEAVY)
        v_table.add_column("Check Description", style="bold")
        v_table.add_column("Expected Outcome", style="dim")
        v_table.add_column("Actual Outcome")
        v_table.add_column("Result", justify="center")

        for v in bundle.verifications:
            res_icon = "[bold green]PASS ✓[/bold green]" if v.passed else "[bold red]FAIL ✗[/bold red]"
            v_table.add_row(v.description, v.expected_outcome, v.actual_outcome, res_icon)

        console.print(v_table)

    console.print(Panel(
        f"[bold white]Summary:[/bold white] {bundle.summary_text}",
        title="[bold green]Outcome Summary[/bold green]",
        border_style="green",
        box=box.ROUNDED
    ))

def cmd_run(args):
    print_banner()
    seed_environment()

    goal = args.goal
    console.print(f"[bold cyan]Initiating Autonomous Worker for objective:[/bold cyan]\n[white]\"{goal}\"[/white]\n")

    # Start company server in background thread if not already running
    import threading
    import uvicorn
    from autonoma.environment.company_server import app

    def start_srv():
        uvicorn.run(app, host=settings.company_host, port=settings.company_port, log_level="warning")

    server_thread = threading.Thread(target=start_srv, daemon=True)
    server_thread.start()
    time.sleep(1.0)  # Wait for server warm-up

    worker = AutonomousWorker(
        llm_provider=args.provider,
        interactive_human=args.interactive,
        default_auto_approve=not args.strict_safety,
        on_step_callback=render_step_trace
    )

    bundle = worker.run(goal)
    render_completion_report(bundle)
    return bundle

def cmd_inspect(args):
    import sqlite3
    conn = sqlite3.connect(str(settings.db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM erp_invoices ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()

    table = Table(title="Corporate ERP Invoices Ledger", box=box.ROUNDED)
    table.add_column("ID", justify="right")
    table.add_column("Invoice #")
    table.add_column("Vendor")
    table.add_column("Amount", justify="right")
    table.add_column("Due Date")
    table.add_column("Status")
    table.add_column("Created At")

    for r in rows:
        table.add_row(
            str(r["id"]),
            r["invoice_number"],
            r["vendor"],
            f"${r['amount']:,.2f}",
            r["due_date"],
            r["status"],
            r["created_at"]
        )
    console.print(table)

def main():
    parser = argparse.ArgumentParser(description="Autonoma - Autonomous AI Task Worker")
    subparsers = parser.add_subparsers(dest="command")

    run_p = subparsers.add_parser("run", help="Run an autonomous task")
    run_p.add_argument("goal", type=str, help="Natural language objective")
    run_p.add_argument("--provider", type=str, default="auto", help="LLM Provider (openai, gemini, anthropic, ollama, deterministic)")
    run_p.add_argument("--interactive", action="store_true", help="Prompt user interactively for HITL approvals and clarifications")
    run_p.add_argument("--strict-safety", action="store_true", help="Disallow auto-approval of high value operations")

    subparsers.add_parser("inspect", help="Inspect company database records")
    subparsers.add_parser("seed", help="Seed/reset environment and sample invoices")

    args = parser.parse_args()

    if args.command == "run":
        cmd_run(args)
    elif args.command == "inspect":
        cmd_inspect(args)
    elif args.command == "seed":
        seed_environment()
        console.print("[green]Environment seeded successfully.[/green]")
    else:
        # Default run with prompt example
        print_banner()
        console.print("[yellow]No command specified. Running prompt's baseline invoice workflow...[/yellow]\n")
        class DefaultArgs:
            goal = "Find the latest invoice from Acme Corp, extract the amount and due date, enter it into our internal system, and tell me once it is done."
            provider = "auto"
            interactive = False
            strict_safety = False
        cmd_run(DefaultArgs())

if __name__ == "__main__":
    main()
