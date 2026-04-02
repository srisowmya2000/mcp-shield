import typer, httpx, json
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="mcp-shield — secure MCP runtime")
console = Console()
BASE = "http://localhost:8000"

@app.command()
def inspect(tool: str, server: str = "cli", policy: str = "default"):
    """Inspect a tool call against a policy."""
    r = httpx.post(f"{BASE}/inspect", json={
        "server_name": server, "policy": policy,
        "tool_call": {"tool_name": tool, "arguments": {}}
    })
    data = r.json()
    color = "red" if data["blocked"] else "green"
    console.print(f"[{color}]{data['decision']}[/{color}] — {data['reason']}")

@app.command()
def audit():
    """Show recent audit log."""
    r = httpx.get(f"{BASE}/audit?limit=20")
    logs = r.json()["logs"]
    table = Table("Time", "Server", "Tool", "Decision", "Reason")
    for log in logs:
        color = "red" if log["decision"] == "BLOCK" else "green"
        table.add_row(log["timestamp"][:19], log["server"], log["tool"],
                      f"[{color}]{log['decision']}[/{color}]", log["reason"][:60])
    console.print(table)

@app.command()
def stats():
    """Show audit stats."""
    r = httpx.get(f"{BASE}/audit/stats")
    console.print(r.json())

if __name__ == "__main__":
    app()
