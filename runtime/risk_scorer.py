from runtime.models import PolicyDecision

HIGH_RISK_TOOLS = {"read_secrets", "ssrf_fetch", "exec_command", "shell_exec", "delete_file", "write_file"}
MEDIUM_RISK_TOOLS = {"read_file", "list_files", "network_request", "http_get"}

def score_server(tool_names: list[str]) -> dict:
    high = [t for t in tool_names if t in HIGH_RISK_TOOLS]
    medium = [t for t in tool_names if t in MEDIUM_RISK_TOOLS]

    if high:
        level = "HIGH"
        score = 90 - (10 * max(0, 3 - len(high)))
    elif medium:
        level = "MEDIUM"
        score = 50
    else:
        level = "LOW"
        score = 10

    return {
        "risk_level": level,
        "risk_score": score,
        "high_risk_tools": high,
        "medium_risk_tools": medium,
        "recommendation": {
            "HIGH": "Do not run without strict policy. Use isolated network.",
            "MEDIUM": "Run with default policy. Monitor closely.",
            "LOW": "Safe to run with standard policy.",
        }[level]
    }
