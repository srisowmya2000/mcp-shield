import subprocess
import json
from runtime.models import RunConfig, SandboxStatus

def launch_sandbox(config: RunConfig) -> SandboxStatus:
    cmd = [
        "docker", "run", "--rm", "--detach",
        "--name", f"mcp-shield-{config.server_name}",
        "--memory=256m", "--cpus=0.5", "--pids-limit=64",
        "--cap-drop=ALL", "--no-new-privileges", "--read-only",
        "--network=none",
        "--tmpfs=/tmp:rw,noexec,nosuid,size=64m",
    ]
    for key, val in config.env_vars.items():
        cmd += ["--env", f"{key}={val}"]
    cmd.append(config.image)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            return SandboxStatus(container_id=result.stdout.strip()[:12],
                                 server_name=config.server_name, status="running", policy=config.policy)
        return SandboxStatus(container_id=None, server_name=config.server_name,
                             status=f"failed: {result.stderr.strip()}", policy=config.policy)
    except FileNotFoundError:
        return SandboxStatus(container_id=None, server_name=config.server_name,
                             status="docker not found", policy=config.policy)

def stop_sandbox(server_name: str) -> dict:
    result = subprocess.run(["docker", "stop", f"mcp-shield-{server_name}"],
                            capture_output=True, text=True)
    return {"stopped": result.returncode == 0}

def list_running_sandboxes() -> list[dict]:
    result = subprocess.run(
        ["docker", "ps", "--filter", "name=mcp-shield-", "--format", "json"],
        capture_output=True, text=True)
    containers = []
    for line in result.stdout.strip().splitlines():
        try:
            containers.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return containers
