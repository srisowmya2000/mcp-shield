import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pytest
from runtime.models import ToolCall, PolicyDecision
from runtime.policy_engine import evaluate

def test_block_tool_not_in_allowlist():
    result = evaluate(ToolCall(tool_name="read_secrets", arguments={}), "default")
    assert result.decision == PolicyDecision.BLOCK

def test_block_ssrf_tool():
    result = evaluate(ToolCall(tool_name="ssrf_fetch", arguments={"url": "http://example.com"}), "default")
    assert result.decision == PolicyDecision.BLOCK

def test_block_exec_command():
    result = evaluate(ToolCall(tool_name="exec_command", arguments={"cmd": "id"}), "default")
    assert result.decision == PolicyDecision.BLOCK

def test_block_aws_metadata_ssrf_in_arg():
    result = evaluate(ToolCall(tool_name="safe_tool", arguments={"url": "http://169.254.169.254/latest/meta-data/"}), "default")
    assert result.decision == PolicyDecision.BLOCK
    assert "169.254.169.254" in result.reason

def test_block_etc_passwd_in_arg():
    result = evaluate(ToolCall(tool_name="safe_tool", arguments={"path": "/etc/passwd"}), "default")
    assert result.decision == PolicyDecision.BLOCK

def test_block_localhost_in_arg():
    result = evaluate(ToolCall(tool_name="safe_tool", arguments={"url": "http://localhost:8080/admin"}), "default")
    assert result.decision == PolicyDecision.BLOCK

def test_block_nested_ssrf():
    result = evaluate(ToolCall(tool_name="safe_tool",
        arguments={"config": {"endpoint": "http://169.254.169.254/iam/credentials"}}), "default")
    assert result.decision == PolicyDecision.BLOCK

def test_allow_safe_tool():
    result = evaluate(ToolCall(tool_name="safe_tool", arguments={"name": "Alice"}), "default")
    assert result.decision == PolicyDecision.ALLOW

def test_allow_get_time():
    result = evaluate(ToolCall(tool_name="get_time", arguments={}), "default")
    assert result.decision == PolicyDecision.ALLOW

def test_allow_list_files():
    result = evaluate(ToolCall(tool_name="list_files", arguments={}), "default")
    assert result.decision == PolicyDecision.ALLOW

def test_strict_blocks_list_files():
    result = evaluate(ToolCall(tool_name="list_files", arguments={}), "strict")
    assert result.decision == PolicyDecision.BLOCK

def test_unknown_policy_raises():
    with pytest.raises(FileNotFoundError):
        evaluate(ToolCall(tool_name="safe_tool", arguments={}), "nonexistent_policy")
