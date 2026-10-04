#!/usr/bin/env python3
"""
Autonoma - 1-Command Demo Runner
Launches the full prototype environment, Company ERP, and Web Control Center.
"""
import sys
import time
import argparse
import threading
import uvicorn
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from autonoma.config import settings
from autonoma.environment.generator import seed_environment
from autonoma.environment.company_server import app as company_app
from autonoma.ui.dashboard_server import dashboard_app
from autonoma.cli import main as cli_main

console = Console()

def run_servers():
    seed_environment()
    console.print(Panel.fit(
        "[bold cyan]AUTONOMA LIVE ENVIRONMENT STARTUP[/bold cyan]\n\n"
        f"🏢 [bold white]Simulated Enterprise Portal (ERP & Desk):[/bold white] [green]http://127.0.0.1:{settings.company_port}[/green]\n"
        f"🤖 [bold white]Autonomous AI Worker Web Dashboard:[/bold white]      [cyan]http://127.0.0.1:{settings.dashboard_port}[/cyan]\n\n"
        "[dim]Press Ctrl+C to terminate the demonstration servers.[/dim]",
        border_style="cyan"
    ))

    # Start Company Server
    t_company = threading.Thread(
        target=lambda: uvicorn.run(company_app, host=settings.company_host, port=settings.company_port, log_level="warning"),
        daemon=True
    )
    t_company.start()

    # Start Dashboard Server
    uvicorn.run(dashboard_app, host=settings.dashboard_host, port=settings.dashboard_port, log_level="warning")

def run_all_scenarios_cli():
    from autonoma.core.agent import AutonomousWorker
    from autonoma.cli import render_step_trace, render_completion_report, print_banner
    from autonoma.environment.company_server import chaos_state

    print_banner()
    seed_environment()

    # Start company server in background
    t = threading.Thread(
        target=lambda: uvicorn.run(company_app, host=settings.company_host, port=settings.company_port, log_level="warning"),
        daemon=True
    )
    t.start()
    time.sleep(1.0)

    scenarios = [
        ("1. Baseline Invoice Entry & Self-Verification", "Find the latest invoice from Acme Corp, extract the amount and due date, enter it into our internal system, and tell me once it is done.", False, False),
        ("2. Flaky Service & Adaptive Recovery", "Find the latest invoice from Acme Corp, extract the amount and due date, enter it into our internal system, and tell me once it is done.", True, False),
        ("3. High-Value Financial Safety Gate (HITL)", "Find the invoice from Apex Systems, extract the amount and due date, and record it into our internal system.", False, False),
        ("4. Ambiguity Clarification Gate", "Find the invoice from Acme, extract amount and due date, and enter it into our internal system.", False, False),
        ("5. Architectural Generalization (Support Disputes)", "Review customer ticket #201 for Globex Corporation, audit their account balance, apply the credit adjustment, and resolve the ticket.", False, False),
    ]

    for title, prompt, chaos, interactive in scenarios:
        console.print(f"\n[bold magenta]══════════════════════════════════════════════════════════════════════[/bold magenta]")
        console.print(f"[bold white]RUNNING DEMO SCENARIO: {title}[/bold white]")
        console.print(f"[bold magenta]══════════════════════════════════════════════════════════════════════[/bold magenta]\n")
        
        chaos_state["flaky_api"] = chaos
        chaos_state["flaky_counter"] = 0

        worker = AutonomousWorker(
            interactive_human=interactive,
            default_auto_approve=True,
            on_step_callback=render_step_trace
        )
        bundle = worker.run(prompt)
        render_completion_report(bundle)
        time.sleep(1.0)

def main():
    parser = argparse.ArgumentParser(description="Autonoma Demo Runner")
    parser.add_argument("--web", action="store_true", help="Launch live split-screen Web Control Center and ERP")
    parser.add_argument("--cli-suite", action="store_true", help="Run full suite of 5 demonstration scenarios in terminal")
    args, unknown = parser.parse_known_args()

    if args.web:
        run_servers()
    elif args.cli_suite:
        run_all_scenarios_cli()
    else:
        # If no arguments provided, run CLI baseline
        cli_main()

if __name__ == "__main__":
    main()
