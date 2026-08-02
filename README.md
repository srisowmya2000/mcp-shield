# MCP Shield 🛡️

> **A local policy-enforcement runtime for MCP tool calls.**

MCP Shield evaluates tool names and arguments against configurable security policies. It returns an `ALLOW` or `BLOCK` decision and records the result in an audit log.

> [!IMPORTANT]
> MCP Shield is an early-stage project. The current release does not automatically discover MCP servers or transparently intercept tool calls from Codex, Claude Code, Cursor, Proxyman, or other MCP clients and servers.

[![Python](https://img.shields.io/badge/python-3.12%2B-blue?style=flat-square)](https://www.python.org/)
[![PyPI](https://img.shields.io/pypi/v/mcpshield-runtime?style=flat-square)](https://pypi.org/project/mcpshield-runtime/)
![Tests](https://img.shields.io/badge/tests-12%20passing-brightgreen?style=flat-square)
![Status](https://img.shields.io/badge/status-alpha-orange?style=flat-square)
[![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)

---

## TL;DR

MCP Shield provides a command-line interface and local REST API for evaluating MCP tool calls against YAML security policies.

It can:

- Allow or block tools using configurable allowlists
- Recursively inspect tool arguments for dangerous patterns
- Detect common SSRF targets, sensitive paths, and unsafe URL schemes
- Record allowed and blocked decisions in an audit log
- Display audit statistics
- Calculate basic risk scores from tool capabilities

Tool calls must currently be submitted through the `mcpshield` CLI or the `/inspect` API. The application making the actual MCP call is responsible for enforcing the returned decision.

---

## Why MCP Tool Calls Need Security Controls

The **Model Context Protocol (MCP)** allows AI applications to connect to external tools and data sources through MCP servers.

Depending on the server, those tools may be able to:

- Read or write files
- Call internal or external APIs
- Query databases
- Access environment variables
- Control browsers
- Execute commands

These capabilities are useful, but a malicious, compromised, or overly permissive server can expose credentials, sensitive files, internal services, or the host system.

MCP Shield provides a policy-decision layer that callers can use before allowing a tool call to continue.

---

## How It Works

1. A caller submits the server name, policy, tool name, and arguments.
2. MCP Shield checks whether the tool is permitted by the selected policy.
3. It recursively scans the arguments for blocked hosts, paths, schemes, and patterns.
4. It returns an `ALLOW` or `BLOCK` decision with a reason.
5. It records the decision in the audit log.

```text
Tool call
   │
   ▼
MCP Shield policy evaluation
   │
   ├── BLOCK → record decision and reject the call
   │
   └── ALLOW → record decision and permit the caller to continue
```

MCP Shield currently evaluates requests; it is not yet a transparent MCP proxy.

---

## Features

- YAML-based policies
- Per-policy tool allowlists
- Recursive argument inspection
- SSRF and sensitive-path pattern detection
- CLI inspection commands
- REST API
- SQLite audit logging
- Audit statistics
- Basic server risk scoring
- Docker sandbox management endpoints
- Experimental Firecracker backend for Linux/KVM environments

---

## Requirements

- Python 3.12 or newer
- macOS, Linux, or Windows for the core API and CLI
- Docker only when using the Docker sandbox backend
- Linux with KVM only when using the experimental Firecracker backend

---

## Installation

### Standard installation

Create and activate a virtual environment:

```bash
python3.12 -m venv ~/mcpshield-env
source ~/mcpshield-env/bin/activate
```

Install MCP Shield:

```bash
python -m pip install --upgrade pip
python -m pip install mcpshield-runtime
```

Verify the installation:

```bash
python --version
mcpshield --help
```

### macOS installation

Some macOS installations still provide Python 3.9 through Xcode. Check your version:

```bash
python3 --version
```

If it is older than Python 3.12, install Python 3.12 with Homebrew:

```bash
brew install python@3.12
```

Create the environment using Homebrew’s interpreter:

```bash
$(brew --prefix python@3.12)/bin/python3.12 -m venv ~/mcpshield-env
source ~/mcpshield-env/bin/activate
python -m pip install --upgrade pip
python -m pip install mcpshield-runtime
```

To reactivate the environment later:

```bash
source ~/mcpshield-env/bin/activate
```

To leave it:

```bash
deactivate
```

---

## Quick Start

MCP Shield currently uses two terminal windows:

- Terminal 1 runs the local API.
- Terminal 2 runs the CLI commands.

### 1. Get the policies

Release `0.1.2` must be started from the cloned repository so the runtime can locate the `policies/` directory:

```bash
cd ~
git clone https://github.com/srisowmya2000/mcp-shield.git
cd ~/mcp-shield
```

If the repository already exists:

```bash
cd ~/mcp-shield
git pull origin main
```

### 2. Terminal 1: Start the API

```bash
cd ~/mcp-shield
source ~/mcpshield-env/bin/activate

export NO_PROXY=localhost,127.0.0.1
export no_proxy=localhost,127.0.0.1

uvicorn runtime.api.main:app \
  --host 127.0.0.1 \
  --port 8000
```

Keep this terminal open. The API will be available at:

```text
http://127.0.0.1:8000
```

Useful pages:

- Health: `http://127.0.0.1:8000/health`
- API documentation: `http://127.0.0.1:8000/docs`
- Dashboard: `http://127.0.0.1:8000/dashboard`

### 3. Terminal 2: Run CLI commands

```bash
source ~/mcpshield-env/bin/activate

export NO_PROXY=localhost,127.0.0.1
export no_proxy=localhost,127.0.0.1
```

Check API health:

```bash
curl --noproxy "*" http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok","service":"mcp-shield","version":"0.1.0"}
```

Inspect a tool that should be blocked:

```bash
mcpshield inspect read_secrets
```

Inspect an allowed tool:

```bash
mcpshield inspect safe_tool
```

View audit statistics and recent decisions:

```bash
mcpshield stats
mcpshield audit
```

Expected results:

```text
read_secrets → BLOCKED
safe_tool    → ALLOWED
```

---

## CLI Usage

### Inspect a tool call

```bash
mcpshield inspect TOOL_NAME
```

Example:

```bash
mcpshield inspect read_secrets
```

Provide tool arguments as JSON:

```bash
mcpshield inspect ssrf_fetch \
  --args '{"url":"http://169.254.169.254/latest/meta-data/"}'
```

Select a policy and server label:

```bash
mcpshield inspect safe_tool \
  --policy default \
  --server demo-server \
  --args '{"name":"Sri"}'
```

### Score tool risk

```bash
mcpshield risk "read_secrets,ssrf_fetch,safe_tool"
```

### View audit records

```bash
mcpshield audit
```

### View audit statistics

```bash
mcpshield stats
```

---

## REST API

### Health check

```bash
curl --noproxy "*" http://127.0.0.1:8000/health
```

### Inspect a tool call

```bash
curl --noproxy "*" \
  -X POST http://127.0.0.1:8000/inspect \
  -H "Content-Type: application/json" \
  -d '{
    "server_name": "demo",
    "policy": "default",
    "tool_call": {
      "tool_name": "read_secrets",
      "arguments": {}
    }
  }'
```

Example blocked response:

```json
{
  "server": "demo",
  "tool": "read_secrets",
  "policy": "default",
  "decision": "BLOCK",
  "reason": "Tool 'read_secrets' is not in the allowed_tools list",
  "blocked": true
}
```

### Audit endpoints

```bash
curl --noproxy "*" http://127.0.0.1:8000/audit
curl --noproxy "*" http://127.0.0.1:8000/audit/stats
```

### Risk scoring

```bash
curl --noproxy "*" \
  -X POST http://127.0.0.1:8000/risk/score \
  -H "Content-Type: application/json" \
  -d '{"tool_names":["read_secrets","ssrf_fetch","safe_tool"]}'
```

---

## Policies

Policies are stored as YAML files inside `policies/`.

Example:

```yaml
allowed_tools:
  - safe_tool
  - list_files
  - get_time

block_network: true
block_env_access: true

blocked_arg_patterns:
  - "169.254.169.254"
  - "169.254.170.2"
  - "localhost"
  - "127.0.0.1"
  - "/etc/passwd"
  - "/etc/shadow"
  - "file://"
  - "gopher://"

max_memory_mb: 256
execution_timeout_seconds: 30
```

The repository includes:

- `default.yaml` — general allowlist and argument checks
- `strict.yaml` — more restrictive policy

Select a policy with:

```bash
mcpshield inspect safe_tool --policy strict
```

> Policy matching is a security control, not a complete guarantee of safety. Use operating-system isolation, least privilege, network restrictions, and careful review of MCP servers.

---

## Troubleshooting

### `No matching distribution found`

Example:

```text
ERROR: Could not find a version that satisfies the requirement mcpshield-runtime
ERROR: No matching distribution found for mcpshield-runtime
```

Check your Python version:

```bash
python3 --version
```

MCP Shield requires Python 3.12 or newer.

On macOS:

```bash
brew install python@3.12

$(brew --prefix python@3.12)/bin/python3.12 \
  -m venv ~/mcpshield-env

source ~/mcpshield-env/bin/activate
python -m pip install mcpshield-runtime
```

### `pip: command not found`

Use pip through the active Python interpreter:

```bash
python -m pip install mcpshield-runtime
```

Do not run:

```bash
pip3 install --upgrade pip3
```

The package is named `pip`, not `pip3`. The correct command is:

```bash
python -m pip install --upgrade pip
```

### `Cannot connect to mcp-shield API`

The CLI requires the local API server.

Start it in another terminal:

```bash
cd ~/mcp-shield
source ~/mcpshield-env/bin/activate

uvicorn runtime.api.main:app \
  --host 127.0.0.1 \
  --port 8000
```

Then verify:

```bash
curl --noproxy "*" http://127.0.0.1:8000/health
```

### `RemoteProtocolError: Server disconnected without sending a response`

A system proxy or an application such as Proxyman may be intercepting localhost traffic.

Set localhost bypass variables in both terminals:

```bash
export NO_PROXY=localhost,127.0.0.1
export no_proxy=localhost,127.0.0.1
```

Also add `localhost` and `127.0.0.1` to the proxy application’s bypass or ignore list.

### `/inspect` returns `404 Not Found`

In release `0.1.2`, policies are resolved relative to the current working directory.

Start Uvicorn from the cloned repository:

```bash
cd ~/mcp-shield

uvicorn runtime.api.main:app \
  --host 127.0.0.1 \
  --port 8000
```

Confirm that the policy files exist:

```bash
ls -la ~/mcp-shield/policies
```

This packaging limitation is expected to be corrected in a later release.

### `KeyError: 'blocked'`

This usually means the `/inspect` endpoint returned an error response instead of a policy decision.

Check the API terminal for a `404` or `500` response.

Confirm that:

- The API is running
- Uvicorn was started from `~/mcp-shield`
- `policies/default.yaml` exists
- Port `8000` is available
- Localhost proxy bypass variables are configured

### `Missing argument 'tool'`

This command is incomplete:

```bash
mcpshield inspect
```

Provide a tool name:

```bash
mcpshield inspect read_secrets
```

### Repository already exists

If cloning returns:

```text
fatal: destination path 'mcp-shield' already exists and is not an empty directory
```

Use the existing repository:

```bash
cd ~/mcp-shield
git pull origin main
```

---

## Current Limitations

The current release does not:

- Automatically discover MCP client configurations
- Automatically discover or scan configured MCP servers
- Transparently intercept MCP protocol traffic
- Automatically integrate with Codex, Claude Code, Cursor, or Proxyman MCP
- Automatically enforce decisions for an external MCP client
- Replace operating-system sandboxing or least-privilege controls

An external caller or future proxy integration must submit the tool call to MCP Shield and honor the returned decision.

---

## Security Model

MCP Shield is intended as a defense-in-depth policy layer. It should not be treated as a complete sandbox or a replacement for:

- Reviewing third-party MCP server code
- Restricting filesystem permissions
- Limiting environment variables and secrets
- Applying outbound network controls
- Running untrusted code in isolated environments
- Monitoring the host and MCP server processes

See [`docs/threat-model.md`](docs/threat-model.md) for additional details.

---

## Development

Clone the repository and install it in editable mode:

```bash
git clone https://github.com/srisowmya2000/mcp-shield.git
cd mcp-shield

python3.12 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -e .
```

Run the tests:

```bash
python -m pip install pytest
pytest tests/ -v
```

Start the development API:

```bash
uvicorn runtime.api.main:app --reload
```

---

## Roadmap

- Package built-in policies correctly for installation from any directory
- Add clearer CLI handling for API error responses
- Add `mcpshield serve` and `mcpshield doctor` commands
- Add structured policy validation
- Add per-tool argument-schema validation
- Add prompt-injection detection
- Add webhook alerts for blocked calls
- Explore an optional MCP proxy and enforcement integration

Automatic MCP client/server discovery belongs to a separate scanner project and is not part of the current MCP Shield runtime.

---

## Responsible Use

Use MCP Shield only with systems, MCP servers, accounts, and environments you own or are authorized to test.

Review policy decisions and server behavior before relying on the project in a sensitive environment.

---

## License

MCP Shield is released under the [MIT License](LICENSE).

---

## Author

**Sri Sowmya Nemani** — security researcher and engineer working in MCP security, application security, detection engineering, and responsible vulnerability disclosure.

- [GitHub](https://github.com/srisowmya2000)
- [PyPI](https://pypi.org/project/mcpshield-runtime/)

Contributions, bug reports, and documentation improvements are welcome.
