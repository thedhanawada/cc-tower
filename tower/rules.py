import re
import fnmatch


def match_rule(rule, tool_name, tool_input):
    """Check if a rule matches the given tool call.

    Args:
        rule: A rule dict from the config.
        tool_name: The name of the tool being called.
        tool_input: The tool's input parameters dict.

    Returns:
        True if the rule matches, False otherwise.
    """
    # Tool name must match
    if rule["tool"] != tool_name:
        return False

    # Check command_pattern for Bash tools
    if "command_pattern" in rule:
        command = tool_input.get("command", "")
        if not re.search(rule["command_pattern"], command):
            return False

    # Check path_pattern for file-based tools
    if "path_pattern" in rule:
        file_path = _extract_path(tool_name, tool_input)
        if file_path is None:
            return False
        if not _match_path_pattern(rule["path_pattern"], file_path):
            return False

    return True


def evaluate_rules(config, tool_name, tool_input):
    """Evaluate rules against a tool call. First match wins.

    Args:
        config: The loaded config dict.
        tool_name: The name of the tool being called.
        tool_input: The tool's input parameters dict.

    Returns:
        Tuple of (action, reason) where action is "allow", "deny", or "ask".
    """
    rules = config.get("rules", [])

    for rule in rules:
        if match_rule(rule, tool_name, tool_input):
            action = rule["action"]
            reason = rule.get("reason", f"Matched rule: {_describe_rule(rule)}")
            return action, reason

    default = config.get("default", "ask")
    return default, f"No matching rule; using default: {default}"


def _extract_path(tool_name, tool_input):
    """Extract the file path from tool input based on tool type."""
    if tool_name in ("Read", "Write", "Edit"):
        return tool_input.get("file_path")
    if tool_name == "Glob":
        return tool_input.get("path") or tool_input.get("pattern")
    if tool_name == "Grep":
        return tool_input.get("path")
    return None


def _match_path_pattern(pattern, path):
    """Match a path against a glob pattern.

    Supports ** for recursive matching and {ext1,ext2} brace expansion.
    """
    # Expand brace patterns like *.{py,js} into multiple patterns
    patterns = _expand_braces(pattern)
    return any(fnmatch.fnmatch(path, p) for p in patterns)


def _expand_braces(pattern):
    """Expand brace patterns like **/*.{py,js} into [**/*.py, **/*.js]."""
    match = re.search(r"\{([^}]+)\}", pattern)
    if not match:
        return [pattern]

    prefix = pattern[: match.start()]
    suffix = pattern[match.end() :]
    alternatives = match.group(1).split(",")

    results = []
    for alt in alternatives:
        expanded = prefix + alt.strip() + suffix
        # Recursively expand in case of nested braces
        results.extend(_expand_braces(expanded))
    return results


def _describe_rule(rule):
    """Create a human-readable description of a rule."""
    parts = [f"{rule['action']} {rule['tool']}"]
    if "command_pattern" in rule:
        parts.append(f"matching /{rule['command_pattern']}/")
    if "path_pattern" in rule:
        parts.append(f"for {rule['path_pattern']}")
    return " ".join(parts)
