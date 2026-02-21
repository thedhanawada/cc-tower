import json
import sys

from tower.config import load_config
from tower.rules import evaluate_rules


def evaluate_from_stdin():
    """Read a tool call from stdin, evaluate rules, and print decision to stdout.

    This is the hook entry point called by Claude Code's PreToolUse hook.

    Input (stdin JSON):
        {"tool_name": "Read", "tool_input": {"file_path": "/tmp/test.txt"}}

    Output (stdout JSON):
        {"hookSpecificOutput": {"hookEventName": "PreToolUse", ...}}
    """
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            _output_decision("ask", "No input received")
            return

        data = json.loads(raw)
        tool_name = data.get("tool_name", "")
        tool_input = data.get("tool_input", {})

        config = load_config()
        action, reason = evaluate_rules(config, tool_name, tool_input)
        _output_decision(action, reason)

    except FileNotFoundError as e:
        _output_decision("ask", str(e))
    except (json.JSONDecodeError, KeyError) as e:
        _output_decision("ask", f"Failed to parse input: {e}")
    except Exception as e:
        # On any unexpected error, fall back to asking the user
        _output_decision("ask", f"Tower error: {e}")


def evaluate(tool_name, tool_input, config=None):
    """Evaluate a tool call against rules programmatically.

    Args:
        tool_name: The name of the tool.
        tool_input: The tool's input parameters.
        config: Optional config dict. If None, loads from file.

    Returns:
        Tuple of (action, reason).
    """
    if config is None:
        config = load_config()
    return evaluate_rules(config, tool_name, tool_input)


def _output_decision(action, reason):
    """Print a hook decision to stdout in Claude Code's expected format."""
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": action,
            "permissionDecisionReason": reason,
        }
    }
    print(json.dumps(output))
