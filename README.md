# mcp-shield 🛡️

> **The security runtime for MCP servers.**  
> Every tool call inspected. Every attack blocked. Every decision logged.

![Python](https://img.shields.io/badge/python-3.12-blue?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)
![Tests](https://img.shields.io/badge/tests-12%20passing-brightgreen?style=flat-square)
![Status](https://img.shields.io/badge/status-active-success?style=flat-square)

---

## What is MCP?

**Model Context Protocol (MCP)** is an open standard that lets AI assistants (like Claude, Cursor, Copilot) connect to external tools and services — file systems, APIs, databases, browsers — through **MCP servers**.

Think of MCP servers as plugins that give AI agents real-world capabilities.

---

## The Problem

MCP servers run as **trusted processes** on your machine with access to:

| Access | Risk |
|---|---|
| 🗂️ Your filesystem | Read `/etc/passwd`, steal SSH keys |
| 🌐 Your network | SSRF to `169.254.169.254` (AWS metadata) |
| 🔑 Your environment variables | Steal API keys, tokens, secrets |
| ⚙️ Shell execution | Run arbitrary commands |

**A malicious or compromised MCP server can silently exfiltrate your secrets, pivot to internal infrastructure, or execute code — and you'd never know.**

This is not theoretical. A real SSRF vulnerability was found in an MCP OAuth HTTP transport implementation that allowed exactly this class of attack.

---

## How mcp-shield Fixes This

mcp-shield sits **between your AI agent and the MCP server** as a policy enforcement layer.  
Before any tool executes, mcp-shield evaluates it. If it's not allowed — it's blocked.

```
AI Agent
   │
   ▼
mcp-shield /inspect
   │
   ├── Tool allowlist check     →  "read_secrets" not allowed → 🚫 BLOCK
   ├── Blocked pattern check    →  "ssrf_fetch" is dangerous  → 🚫 BLOCK  
   ├── Argument scanning        →  "169.254.169.254" in args  → 🚫 BLOCK
   │
   └── Passed all checks        →  ✅ ALLOW → MCP Server executes
                                        │
                                        ▼
                                   Audit Log (SQLite)
```

Every decision — ALLOW or BLOCK — is logged with a full audit trail.

---

## Live Demo

```bash
# Start mcp-shield
uvicorn runtime.api.main:app --reload

# 🚫 Attempt secret theft → BLOCKED
curl -X POST http://localhost:8000/inspect \
  -H "Content-Type: application/json" \
  -d '{"server_name":"evil","policy":"default","tool_call":{"tool_name":"read_secrets","arguments":{}}}'

# → {"decision":"BLOCK","reason":"Tool 'read_secrets' is not in the allowed_tools list","blocked":true}

# 🚫 Attempt SSRF to AWS metadata endpoint → BLOCKED
curl -X POST http://localhost:8000/inspect \
  -H "Content-Type: application/json" \
  -d '{"server_name":"evil","policy":"default","tool_call":{"tool_name":"ssrf_fetch","arguments":{"url":"http://169.254.169.254/latest/meta-data/"}}}'

# → {"decision":"BLOCK","reason":"Argument contains blocked pattern: '169.254.169.254'","blocked":true}

# ✅ Safe tool → ALLOWED
curl -X POST http://localhost:8000/inspect \
  -H "Content-Type: application/json" \
  -d '{"server_name":"safe","policy":"default","tool_call":{"tool_name":"safe_tool","arguments":{"name":"Sri"}}}'

# → {"decision":"ALLOW","reason":"Passed all policy checks","blocked":false}
```

---

## Key Features

| Feature | Description |
|---|---|
| 🔒 **Policy Engine** | YAML-based allowlists + blocked patterns, per-server policies |
| 🔍 **Argument Scanning** | Recursively scans nested args for SSRF, path traversal, dangerous patterns |
| 📋 **Audit Logger** | Every decision logged to SQLite with timestamp, server, tool, reason |
| 🐳 **Docker Sandbox** | Hardened containers: `--cap-drop=ALL`, `--network=none`, `--read-only` |
| 📊 **Risk Scorer** | Scores MCP servers LOW / MEDIUM / HIGH based on tool capabilities |
| 🖥️ **Live Dashboard** | Real-time web UI showing live block/allow feed at `/dashboard` |
| ⚡ **CLI** | `mcpshield inspect`, `mcpshield audit`, `mcpshield stats`, `mcpshield risk` |

---

## Policies

Policies are simple YAML files. Drop one in `policies/` and reference it by name.

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
  - "169.254.170.2"     # ECS metadata SSRF
  - "localhost"
  - "127.0.0.1"
  - "/etc/passwd"
  - "/etc/shadow"
  - "file://"
  - "gopher://"

max_memory_mb: 256
execution_timeout_seconds: 30
```

Switch policy per server:
```bash
POST /inspect  →  { "policy": "strict", ... }
```

---

## Architecture

```
mcp-shield/
├── runtime/
│   ├── api/
│   │   └── main.py            # FastAPI — /inspect /audit /sandbox /dashboard
│   ├── policy_engine.py       # YAML policy loader + evaluator
│   ├── audit_logger.py        # SQLite decision log
│   ├── risk_scorer.py         # LOW/MEDIUM/HIGH risk scoring
│   ├── cli.py                 # Typer CLI — inspect/audit/stats/risk
│   ├── models.py              # Pydantic schemas
│   └── sandbox/
│       ├── base.py            # Abstract backend interface
│       └── docker_backend.py  # Hardened Docker sandbox
├── policies/
│   ├── default.yaml           # Standard policy
│   └── strict.yaml            # Zero-trust policy
├── examples/
│   ├── malicious_mcp_server/  # Demo attacker (SSRF + secret theft + exec)
│   └── safe_mcp_server/       # Demo benign server
└── tests/                     # 12 tests — all passing
```

---

## Quickstart

```bash
# 1. Clone
git clone https://github.com/srisowmya2000/mcp-shield
cd mcp-shield

# 2. Install
python3 -m venv .venv && source .venv/bin/activate
pip install fastapi uvicorn pydantic pydantic-settings mcp httpx pyyaml

# 3. Start
uvicorn runtime.api.main:app --reload

# 4. Open
# API docs  → http://localhost:8000/docs
# Dashboard → http://localhost:8000/dashboard
```

---

## CLI

```bash
# Inspect a tool call
python3 -m runtime.cli inspect read_secrets
# → 🚫 BLOCKED — Tool 'read_secrets' is not in the allowed_tools list

# Score a server's risk
python3 -m runtime.cli risk "read_secrets,ssrf_fetch,safe_tool"
# → 🔴 HIGH RISK (score: 80)

# View audit log
python3 -m runtime.cli audit

# View stats
python3 -m runtime.cli stats
# → Total: 6 | Allowed: 2 | Blocked: 4 (67% block rate)
```

---

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Service health check |
| `/inspect` | POST | Evaluate tool call → ALLOW / BLOCK |
| `/audit` | GET | Recent audit log entries |
| `/audit/stats` | GET | Total / allowed / blocked counts |
| `/risk/score` | POST | Score server risk by tool list |
| `/sandbox/launch` | POST | Launch MCP server in hardened Docker |
| `/sandbox/stop/{name}` | POST | Stop a running sandbox |
| `/sandbox/list` | GET | List running sandboxes |
| `/dashboard` | GET | Live real-time dashboard |

---

## Tests

```bash
pip install pytest
pytest tests/ -v
# 12 passed in 0.11s
```

Covers: tool allowlist blocking, SSRF argument detection, nested arg scanning, strict policy, edge cases.

---

## Roadmap

- [x] Policy engine (allowlist + pattern scanning)
- [x] Audit logger (SQLite)
- [x] FastAPI REST surface
- [x] Docker sandbox backend (hardened)
- [x] Demo malicious MCP server
- [x] Risk scorer (LOW / MEDIUM / HIGH)
- [x] CLI (`mcpshield inspect`, `audit`, `stats`, `risk`)
- [x] Real-time dashboard
- [ ] Firecracker microVM backend
- [ ] PyPI package (`pip install mcp-shield`)
- [ ] `threat-model.md`

---


