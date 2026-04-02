from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from runtime.models import ToolCall, RunConfig, PolicyDecision
from runtime.policy_engine import evaluate
from runtime.audit_logger import log_decision, get_recent_logs, get_stats
from runtime.sandbox.docker_backend import launch_sandbox, stop_sandbox, list_running_sandboxes

app = FastAPI(title="mcp-shield", description="Secure MCP runtime with policy enforcement", version="0.1.0")

class InspectRequest(BaseModel):
    server_name: str
    policy: str = "default"
    tool_call: ToolCall

class LaunchRequest(BaseModel):
    server_name: str
    image: str
    policy: str = "default"
    env_vars: dict[str, str] = {}

@app.get("/health")
def health():
    return {"status": "ok", "service": "mcp-shield", "version": "0.1.0"}

@app.post("/inspect")
def inspect_tool_call(req: InspectRequest):
    try:
        result = evaluate(req.tool_call, req.policy)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    log_decision(req.server_name, req.tool_call, result)
    return {"server": req.server_name, "tool": req.tool_call.tool_name,
            "policy": req.policy, "decision": result.decision,
            "reason": result.reason, "blocked": result.decision == PolicyDecision.BLOCK}

@app.get("/audit")
def audit_log(limit: int = 50):
    return {"logs": get_recent_logs(limit)}

@app.get("/audit/stats")
def audit_stats():
    return get_stats()

@app.post("/sandbox/launch")
def launch(req: LaunchRequest):
    config = RunConfig(server_name=req.server_name, image=req.image,
                       policy=req.policy, env_vars=req.env_vars)
    return launch_sandbox(config)

@app.post("/sandbox/stop/{server_name}")
def stop(server_name: str):
    return stop_sandbox(server_name)

@app.get("/sandbox/list")
def list_sandboxes():
    return {"sandboxes": list_running_sandboxes()}

from runtime.risk_scorer import score_server

class RiskRequest(BaseModel):
    tool_names: list[str]

@app.post("/risk/score")
def risk_score(req: RiskRequest):
    return score_server(req.tool_names)

from fastapi.responses import FileResponse
from pathlib import Path

@app.get("/dashboard", tags=["dashboard"])
def dashboard():
    """Live real-time decision dashboard."""
    return FileResponse(Path(__file__).parent.parent / "static" / "dashboard.html")
