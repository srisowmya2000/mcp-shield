"""Demo safe MCP server — all tools are benign and should be ALLOWED."""
import asyncio
from datetime import datetime, timezone
import mcp.server.stdio
import mcp.types as types
from mcp.server import Server

app = Server("safe-demo-server")

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(name="safe_tool", description="Returns a greeting",
                   inputSchema={"type": "object", "properties": {"name": {"type": "string"}}}),
        types.Tool(name="get_time", description="Returns current UTC time",
                   inputSchema={"type": "object", "properties": {}}),
        types.Tool(name="list_files", description="Lists files in /tmp",
                   inputSchema={"type": "object", "properties": {}}),
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "safe_tool":
        return [types.TextContent(type="text", text=f"Hello, {arguments.get('name', 'world')}!")]
    if name == "get_time":
        return [types.TextContent(type="text", text=datetime.now(timezone.utc).isoformat())]
    if name == "list_files":
        import os
        return [types.TextContent(type="text", text=str(os.listdir("/tmp")))]
    return [types.TextContent(type="text", text="Unknown tool")]

if __name__ == "__main__":
    asyncio.run(mcp.server.stdio.run(app))
