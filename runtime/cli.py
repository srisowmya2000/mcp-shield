import typer
import httpx
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

app = typer.Typer(
    name="mcpshield",
    help="🛡️  mcp-shield — secure MCP runtime CLI",
    add_completion=False
)
console = Console()
BASE = "http://localhost:8000"


@app.command()
def inspect(
    tool: str = typer.Argument(..., help="Tool name to inspect"),
    policy: str = typer.Option("default", "--policy", "-p", help="Policy to evaluate against"),
    server: str = typer.Option("cli", "--server", "-s", help="Server name label"),
    args: str = typer.Option("{}", "--args", "-a", help='Tool arguments as JSON string'),
):
    """Inspect a tool call against a policy. Returns ALLOW or BLOCK."""
    try:
        arguments = json.loads(args)
    except json.JSONDecodeError:
        console.print("[red]Error: --args must be valid JSON[/red]")
        raise typer.Exit(1)

    try:
        r = httpx.post(f"{BASE}/inspect", json={
            "server_name": server,
            "policy": policy,
            "tool_call": {"tool_name": tool, "arguments": arguments}
        })
        data = r.json()
        if data["blocked"]:
            console.print(Panel(
                f"[bold red]🚫 BLOCKED[/bold red]\n\n"
                f"Tool:    [yellow]{tool}[/yellow]\n"
                f"Policy:  {policy}\n"
                f"Reason:  {data['reason']}",
                title="mcp-shield decision", border_style="red"
            ))
        else:
            console.print(Panel(
                f"[bold green]✅ ALLOWED[/bold green]\n\n"
                f"Tool:    [yellow]{tool}[/yellow]\n"
                f"Policy:  {policy}\n"
                f"Reason:  {data['reason']}",
                title="mcp-shield decision", border_style="green"
            ))
    except httpx.ConnectError:
        console.print("[red]Error: Cannot connect to mcp-shield API. Is it running?[/red]")
        console.print("[dim]Run: uvicorn runtime.api.main:app --reload[/dim]")
        raise typer.Exit(1)


@app.command()
def audit(
    limit: int = typer.Option(20, "--limit", "-n", help="Number of recent entries to show"),
):
    """Show recent audit log entries."""
    try:
        r = httpx.get(f"{BASE}/audit?limit={limit}")
        logs = r.json()["logs"]

        if not logs:
            console.print("[dim]No audit entries yet.[/dim]")
            return

        table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
        table.add_column("Time", style="dim", width=20)
        table.add_column("Server", width=16)
        table.add_column("Tool", width=18)
        table.add_column("Decision", width=10)
        table.add_column("Reason")

        for log in logs:
            decision_str = (
                "[bold red]🚫 BLOCK[/bold red]"
                if log["decision"] == "BLOCK"
                else "[bold green]✅ ALLOW[/bold green]"
            )
            table.add_row(
                log["timestamp"][:19].replace("T", " "),
                log["server"],
                log["tool"],
                decision_str,
                log["reason"][:55] + ("…" if len(log["reason"]) > 55 else "")
            )

        console.print(table)
    except httpx.ConnectError:
        console.print("[red]Error: Cannot connect to mcp-shield API.[/red]")
        raise typer.Exit(1)


@app.command()
def stats():
    """Show audit statistics — total, allowed, blocked."""
    try:
        r = httpx.get(f"{BASE}/audit/stats")
        data = r.json()
        total = data["total"]
        allowed = data["allowed"]
        blocked = data["blocked"]
        pct = f"{(blocked/total*100):.0f}%" if total > 0 else "0%"

        console.print(Panel(
            f"[bold]Total decisions:[/bold]  {total}\n"
            f"[green]✅ Allowed:[/green]        {allowed}\n"
            f"[red]🚫 Blocked:[/red]        {blocked}  ({pct} block rate)",
            title="🛡️  mcp-shield audit stats",
            border_style="cyan"
        ))
    except httpx.ConnectError:
        console.print("[red]Error: Cannot connect to mcp-shield API.[/red]")
        raise typer.Exit(1)


@app.command()
def risk(
    tools: str = typer.Argument(..., help="Comma-separated list of tool names to score"),
):
    """Score an MCP server's risk level based on its tools."""
    tool_list = [t.strip() for t in tools.split(",")]
    try:
        r = httpx.post(f"{BASE}/risk/score", json={"tool_names": tool_list})
        data = r.json()

        color = {"HIGH": "red", "MEDIUM": "yellow", "LOW": "green"}[data["risk_level"]]
        console.print(Panel(
            f"[bold {color}]{data['risk_level']} RISK (score: {data['risk_score']})[/bold {color}]\n\n"
            f"[red]High-risk tools:[/red]   {data['high_risk_tools'] or 'none'}\n"
            f"[yellow]Medium-risk tools:[/yellow] {data['medium_risk_tools'] or 'none'}\n\n"
            f"[dim]{data['recommendation']}[/dim]",
            title="🛡️  mcp-shield risk score",
            border_style=color
        ))
    except httpx.ConnectError:
        console.print("[red]Error: Cannot connect to mcp-shield API.[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
