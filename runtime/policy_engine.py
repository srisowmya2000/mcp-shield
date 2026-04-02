import yaml
from pathlib import Path
from runtime.models import ToolCall, PolicyResult, PolicyDecision

POLICIES_DIR = Path(__file__).parent.parent / "policies"

def load_policy(name: str) -> dict:
    path = POLICIES_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Policy file not found: {name}.yaml")
    with open(path) as f:
        return yaml.safe_load(f)

def evaluate(tool_call: ToolCall, policy_name: str = "default") -> PolicyResult:
    policy = load_policy(policy_name)
    allowed_tools = policy.get("allowed_tools", [])
    blocked_patterns = policy.get("blocked_tool_patterns", [])
    blocked_arg_patterns = policy.get("blocked_arg_patterns", [])

    if tool_call.tool_name not in allowed_tools:
        return PolicyResult(
            decision=PolicyDecision.BLOCK,
            reason=f"Tool '{tool_call.tool_name}' is not in the allowed_tools list"
        )

    for pattern in blocked_patterns:
        if pattern.lower() in tool_call.tool_name.lower():
            return PolicyResult(
                decision=PolicyDecision.BLOCK,
                reason=f"Tool name matches blocked pattern: '{pattern}'"
            )

    all_values = _flatten_args(tool_call.arguments)
    for val in all_values:
        for pattern in blocked_arg_patterns:
            if pattern.lower() in val.lower():
                return PolicyResult(
                    decision=PolicyDecision.BLOCK,
                    reason=f"Argument contains blocked pattern: '{pattern}' — possible SSRF or path traversal"
                )

    return PolicyResult(decision=PolicyDecision.ALLOW, reason="Passed all policy checks")

def _flatten_args(args: dict, depth: int = 0) -> list[str]:
    if depth > 5:
        return []
    result = []
    for val in args.values():
        if isinstance(val, dict):
            result.extend(_flatten_args(val, depth + 1))
        elif isinstance(val, list):
            for item in val:
                result.append(str(item))
        else:
            result.append(str(val))
    return result
