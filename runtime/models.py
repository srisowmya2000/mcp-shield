from pydantic import BaseModel
from typing import Any, Optional
from enum import Enum

class PolicyDecision(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"

class ToolCall(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = {}

class PolicyResult(BaseModel):
    decision: PolicyDecision
    reason: str

class RunConfig(BaseModel):
    server_name: str
    image: str
    policy: str = "default"
    env_vars: dict[str, str] = {}

class SandboxStatus(BaseModel):
    container_id: Optional[str]
    server_name: str
    status: str
    policy: str
