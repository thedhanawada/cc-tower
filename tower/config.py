import os
import yaml

CONFIG_FILENAME = "tower-rules.yml"

_cached_config = None
_cached_config_path = None


def find_config_path():
    """Search for tower-rules.yml in current dir, .claude/, ~/.claude/."""
    search_paths = [
        os.path.join(os.getcwd(), CONFIG_FILENAME),
        os.path.join(os.getcwd(), ".claude", CONFIG_FILENAME),
        os.path.join(os.path.expanduser("~"), ".claude", CONFIG_FILENAME),
    ]
    for path in search_paths:
        if os.path.isfile(path):
            return path
    return None


def load_config(path=None):
    """Load and validate the tower-rules.yml config.

    Args:
        path: Explicit path to config file. If None, searches standard locations.

    Returns:
        Parsed config dict.

    Raises:
        FileNotFoundError: If no config file is found.
        ValueError: If config is invalid.
    """
    global _cached_config, _cached_config_path

    if path is None:
        path = find_config_path()
    if path is None:
        raise FileNotFoundError(
            f"No {CONFIG_FILENAME} found. Run 'tower init' to create one."
        )

    path = os.path.abspath(path)

    if _cached_config is not None and _cached_config_path == path:
        return _cached_config

    with open(path) as f:
        config = yaml.safe_load(f)

    _validate_config(config)
    _cached_config = config
    _cached_config_path = path
    return config


def _validate_config(config):
    """Validate the config structure."""
    if not isinstance(config, dict):
        raise ValueError("Config must be a YAML mapping")
    if "version" not in config:
        raise ValueError("Config must have a 'version' field")
    if config["version"] != 1:
        raise ValueError(f"Unsupported config version: {config['version']}")

    default = config.get("default", "ask")
    if default not in ("allow", "deny", "ask"):
        raise ValueError(f"Invalid default action: {default}")

    rules = config.get("rules", [])
    if not isinstance(rules, list):
        raise ValueError("'rules' must be a list")

    valid_actions = {"allow", "deny", "ask"}
    for i, rule in enumerate(rules):
        if not isinstance(rule, dict):
            raise ValueError(f"Rule {i} must be a mapping")
        if "tool" not in rule:
            raise ValueError(f"Rule {i} must have a 'tool' field")
        if "action" not in rule:
            raise ValueError(f"Rule {i} must have an 'action' field")
        if rule["action"] not in valid_actions:
            raise ValueError(f"Rule {i} has invalid action: {rule['action']}")


def save_config(config, path=None):
    """Write config dict back to tower-rules.yml.

    Args:
        config: The config dict to save.
        path: Path to write to. If None, uses find_config_path().

    Raises:
        FileNotFoundError: If no config path can be determined.
    """
    if path is None:
        path = find_config_path()
    if path is None:
        raise FileNotFoundError(
            f"No {CONFIG_FILENAME} found. Run 'tower init' to create one."
        )

    with open(path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    clear_cache()


def clear_cache():
    """Clear the cached config."""
    global _cached_config, _cached_config_path
    _cached_config = None
    _cached_config_path = None


DEFAULT_CONFIG = """\
version: 1
default: ask  # what to do when no rule matches: allow | deny | ask

rules:
  # Allow all file reads
  - tool: Read
    action: allow

  # Allow glob/grep (search is safe)
  - tool: Glob
    action: allow
  - tool: Grep
    action: allow

  # Allow safe bash commands
  - tool: Bash
    command_pattern: "^(ls|cat|git status|git diff|npm test|pytest).*"
    action: allow

  # Deny destructive bash commands
  - tool: Bash
    command_pattern: "rm -rf|git push --force|DROP TABLE"
    action: deny
    reason: "Destructive command blocked by Tower"

  # Allow writes only to certain extensions
  - tool: Write
    path_pattern: "**/*.{py,js,ts,json,yml,yaml,md}"
    action: allow
"""
