# mcp-shield 🛡️

**Secure runtime for MCP (Model Context Protocol) servers.**  
Intercepts tool calls, enforces YAML policies, blocks malicious actions, and logs every decision.

## The problem

MCP servers run as trusted processes with access to your filesystem, environment variables, and network. A malicious or compromised MCP server can:
- Exfiltrate secrets via `read_secrets` or env var access
- Perform SSRF attacks against cloud metadata endpoints (e.g. `http://169.254.169.254`)
- Execute arbitrary commands via `exec_command`

This is a real attack class — see [HackerOne #3623357](https://hackerone.com/reports/3623357): SSRF in MCP HTTP transport OAuth implementation.

**mcp-shield sits in front of your MCP servers and blocks these attacks before they execute.**

## Demo
```bash
# Start the runtime
uvicorn runtime.api.main:app --reload

# Attempt secret theft → BLOCKED
curl -X POST http://localhost:8000/inspect \
  -H "Content-Type: application/json" \
  -d '{"server_name":"evil","policy":"default","tool_call":{"tool_name":"read_secrets","arguments":{}}}'
# → {"decision":"BLOCK","reason":"Tool 'read_secrets' is not in the allowed_tools list","blocked":true}

# Attempt SSRF to AWS metadata → BLOCKED  
curl -X POST http://localhost:8000/inspect \
  -H "Content-Type: application/json" \
  -d '{"server_name":"evil","policy":"default","tool_call":{"tool_name":"ssrf_fetch","arguments":{"url":"http://169.254.169.254/latest/meta-data/"}}}'
# → {"decision":"BLOCK","reason":"Tool 'ssrf_fetch' is not in the allowed_tools list","blocked":true}

# Safe tool → ALLOWED
curl -X POST http://localhost:8000/inspect \
  -H "Content-Type: application/json" \
  -d '{"server_name":"safe","policy":"default","tool_call":{"tool_name":"safe_tool","arguments":{"name":"Sri"}}}'
# → {"decision":"ALLOW","reason":"Passed all policy checks","blocked":false}
```

## How it works
```
MCP Client → mcp-shield /inspect → Policy Engine → ALLOW/BLOCK → Audit Log
                                         ↓
                                    YAML Policy
                                  (allowlist + patterns)
```

Every tool call is evaluated against a YAML policy before execution:
1. **Tool allowlist** — only explicitly allowed tools can run
2. **Blocked tool patterns** — dangerous tool names are always blocked
3. **Argument scanning** — arguments are scanned for SSRF targets, path traversal, and dangerous patterns (recursive, handles nested dicts)

## Policies
```yaml
# policies/default.yaml
allowed_tools:
  - safe_tool
  - list_files
  - get_time

block_network: true
block_env_access: true

blocked_arg_patterns:
  - "169.254.169.254"   # AWS metadata SSRF
  - "localhost"
  - "/etc/passwd"
  - "file://"
```

Switch policies per server: `POST /inspect` with `"policy": "strict"`.

## API

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Service health |
| `/inspect` | POST | Evaluate a tool call → ALLOW/BLOCK |
| `/audit` | GET | Recent audit log entries |
| `/audit/stats` | GET | Total / allowed / blocked counts |
| `/sandbox/launch` | POST | Launch MCP server in hardened Docker container |
| `/sandbox/stop/{name}` | POST | Stop a running sandbox |
| `/sandbox/list` | GET | List running sandboxes |

## Docker sandbox

MCP servers are launched with:
- `--cap-drop=ALL` — no Linux capabilities
- `--no-new-privileges` — no privilege escalation
- `--read-only` — immutable filesystem
- `--network=none` — no network access
- `--memory=256m --cpus=0.5 --pids-limit=64` — resource limits

## Quickstart
```bash
git clone https://github.com/srisowmya2000/mcp-shield
cd mcp-shield
python3 -m venv .venv && source .venv/bin/activate
pip install fastapi uvicorn pydantic pydantic-settings mcp httpx pyyaml
uvicorn runtime.api.main:app --reload
# → http://localhost:8000/docs
```

## Tests
```bash
pip install pytest
pytest tests/ -v
# 12 passed
```

## Roadmap

- [x] Policy engine (allowlist + pattern scanning)
- [x] Audit logger (SQLite)
- [x] FastAPI REST surface
- [x] Docker sandbox backend (hardened)
- [x] Demo malicious MCP server
- [ ] Risk scorer (low/medium/high per server)
- [ ] Firecracker microVM backend
- [ ] CLI (`mcpshield run`, `mcpshield audit`)
- [ ] Real-time dashboard

## Architecture
```
mcp-shield/
├── runtime/
│   ├── api/main.py          # FastAPI endpoints
│   ├── policy_engine.py     # YAML policy evaluation
│   ├── audit_logger.py      # SQLite decision log
│   ├── models.py            # Pydantic schemas
│   └── sandbox/
│       ├── docker_backend.py  # Hardened Docker launch
│       └── base.py            # Abstract backend interface
├── policies/
│   ├── default.yaml
│   └── strict.yaml
└── examples/
    ├── malicious_mcp_server/  # Demo attacker server
    └── safe_mcp_server/       # Demo benign server
```
