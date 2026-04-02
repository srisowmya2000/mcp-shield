import sqlite3
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from runtime.models import ToolCall, PolicyResult, PolicyDecision

DB_PATH = Path(__file__).parent.parent / "reports" / "audit.db"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%Y-%m-%dT%H:%M:%S")
logger = logging.getLogger("mcp-shield")

def init_db():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   TEXT NOT NULL,
            server_name TEXT NOT NULL,
            tool_name   TEXT NOT NULL,
            arguments   TEXT,
            decision    TEXT NOT NULL,
            reason      TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def log_decision(server_name: str, tool_call: ToolCall, result: PolicyResult) -> None:
    init_db()
    timestamp = datetime.now(timezone.utc).isoformat()
    icon = "✅" if result.decision == PolicyDecision.ALLOW else "🚫"
    entry = {"timestamp": timestamp, "server": server_name, "tool": tool_call.tool_name,
             "decision": result.decision.value, "reason": result.reason}
    logger.info(f"{icon} {json.dumps(entry)}")
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO audit_log (timestamp, server_name, tool_name, arguments, decision, reason)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (timestamp, server_name, tool_call.tool_name, json.dumps(tool_call.arguments),
          result.decision.value, result.reason))
    conn.commit()
    conn.close()

def get_recent_logs(limit: int = 50) -> list[dict]:
    if not DB_PATH.exists():
        return []
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("""
        SELECT timestamp, server_name, tool_name, arguments, decision, reason
        FROM audit_log ORDER BY id DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [{"timestamp": r[0], "server": r[1], "tool": r[2],
             "arguments": json.loads(r[3]) if r[3] else {}, "decision": r[4], "reason": r[5]}
            for r in rows]

def get_stats() -> dict:
    if not DB_PATH.exists():
        return {"total": 0, "allowed": 0, "blocked": 0}
    conn = sqlite3.connect(DB_PATH)
    total = conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
    allowed = conn.execute("SELECT COUNT(*) FROM audit_log WHERE decision='ALLOW'").fetchone()[0]
    blocked = conn.execute("SELECT COUNT(*) FROM audit_log WHERE decision='BLOCK'").fetchone()[0]
    conn.close()
    return {"total": total, "allowed": allowed, "blocked": blocked}
