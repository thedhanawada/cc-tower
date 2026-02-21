"""Interactive configuration UI for Tower using InquirerPy."""

from InquirerPy import inquirer
from InquirerPy.separator import Separator

from tower.config import find_config_path, load_config, save_config


TOOL_CHOICES = [
    "Bash",
    "Read",
    "Write",
    "Edit",
    "Glob",
    "Grep",
    "NotebookEdit",
    "Task",
    "WebFetch",
    "WebSearch",
]

ACTION_CHOICES = ["allow", "deny", "ask"]


def run_interactive_config():
    """Launch the interactive Tower config menu."""
    config_path = find_config_path()
    if config_path is None:
        print("No tower-rules.yml found. Run 'tower init' first.")
        return 1

    config = load_config(config_path)
    print(f"Editing: {config_path}\n")

    while True:
        action = inquirer.select(
            message="Tower Config",
            choices=[
                "View rules",
                "Add rule",
                "Edit rule",
                "Delete rule",
                "Change default action",
                "Reset to defaults",
                Separator(),
                "Save & exit",
                "Exit without saving",
            ],
        ).execute()

        if action == "View rules":
            _view_rules(config)
        elif action == "Add rule":
            _add_rule(config)
        elif action == "Edit rule":
            _edit_rule(config)
        elif action == "Delete rule":
            _delete_rule(config)
        elif action == "Change default action":
            _change_default(config)
        elif action == "Reset to defaults":
            if inquirer.confirm(message="Reset all rules to defaults?", default=False).execute():
                from tower.config import DEFAULT_CONFIG
                import yaml
                config = yaml.safe_load(DEFAULT_CONFIG)
                print("Config reset to defaults.")
        elif action == "Save & exit":
            save_config(config, config_path)
            print(f"Saved to {config_path}")
            return 0
        elif action == "Exit without saving":
            return 0


def _view_rules(config):
    """Pretty-print current rules."""
    print(f"\nDefault action: {config.get('default', 'ask')}")
    rules = config.get("rules", [])
    if not rules:
        print("No rules defined.\n")
        return

    print(f"Rules ({len(rules)}):\n")
    for i, rule in enumerate(rules):
        parts = [f"  {i + 1}. {rule['action'].upper():5s} {rule['tool']}"]
        if "command_pattern" in rule:
            parts.append(f"     command: /{rule['command_pattern']}/")
        if "path_pattern" in rule:
            parts.append(f"     path: {rule['path_pattern']}")
        if "reason" in rule:
            parts.append(f"     reason: {rule['reason']}")
        print("\n".join(parts))
    print()


def _format_rule(i, rule):
    """Format a rule for display in selection lists."""
    desc = f"{rule['action'].upper():5s} {rule['tool']}"
    if "command_pattern" in rule:
        desc += f"  cmd:/{rule['command_pattern']}/"
    if "path_pattern" in rule:
        desc += f"  path:{rule['path_pattern']}"
    return f"{i + 1}. {desc}"


def _add_rule(config):
    """Interactively add a new rule."""
    tool = inquirer.select(
        message="Tool name:",
        choices=TOOL_CHOICES,
    ).execute()

    action = inquirer.select(
        message="Action:",
        choices=ACTION_CHOICES,
    ).execute()

    rule = {"tool": tool, "action": action}

    # Optional patterns
    if tool == "Bash":
        pattern = inquirer.text(
            message="Command pattern (regex, leave empty to match all):",
        ).execute().strip()
        if pattern:
            rule["command_pattern"] = pattern

    if tool in ("Read", "Write", "Edit", "Glob", "Grep"):
        pattern = inquirer.text(
            message="Path pattern (glob, leave empty to match all):",
        ).execute().strip()
        if pattern:
            rule["path_pattern"] = pattern

    reason = inquirer.text(
        message="Reason (optional):",
    ).execute().strip()
    if reason:
        rule["reason"] = reason

    config.setdefault("rules", []).append(rule)
    print(f"Added: {action.upper()} {tool}\n")


def _edit_rule(config):
    """Interactively edit an existing rule."""
    rules = config.get("rules", [])
    if not rules:
        print("No rules to edit.\n")
        return

    choices = [_format_rule(i, r) for i, r in enumerate(rules)]
    choices.append("Cancel")

    selected = inquirer.select(
        message="Select rule to edit:",
        choices=choices,
    ).execute()

    if selected == "Cancel":
        return

    idx = choices.index(selected)
    rule = rules[idx]

    # Edit tool
    rule["tool"] = inquirer.select(
        message="Tool name:",
        choices=TOOL_CHOICES,
        default=rule["tool"],
    ).execute()

    # Edit action
    rule["action"] = inquirer.select(
        message="Action:",
        choices=ACTION_CHOICES,
        default=rule["action"],
    ).execute()

    # Edit command_pattern
    if rule["tool"] == "Bash":
        current = rule.get("command_pattern", "")
        new_val = inquirer.text(
            message="Command pattern (regex):",
            default=current,
        ).execute().strip()
        if new_val:
            rule["command_pattern"] = new_val
        else:
            rule.pop("command_pattern", None)
    else:
        rule.pop("command_pattern", None)

    # Edit path_pattern
    if rule["tool"] in ("Read", "Write", "Edit", "Glob", "Grep"):
        current = rule.get("path_pattern", "")
        new_val = inquirer.text(
            message="Path pattern (glob):",
            default=current,
        ).execute().strip()
        if new_val:
            rule["path_pattern"] = new_val
        else:
            rule.pop("path_pattern", None)
    else:
        rule.pop("path_pattern", None)

    # Edit reason
    current_reason = rule.get("reason", "")
    new_reason = inquirer.text(
        message="Reason (optional):",
        default=current_reason,
    ).execute().strip()
    if new_reason:
        rule["reason"] = new_reason
    else:
        rule.pop("reason", None)

    print("Rule updated.\n")


def _delete_rule(config):
    """Interactively delete a rule."""
    rules = config.get("rules", [])
    if not rules:
        print("No rules to delete.\n")
        return

    choices = [_format_rule(i, r) for i, r in enumerate(rules)]
    choices.append("Cancel")

    selected = inquirer.select(
        message="Select rule to delete:",
        choices=choices,
    ).execute()

    if selected == "Cancel":
        return

    idx = choices.index(selected)
    removed = rules.pop(idx)
    print(f"Deleted: {removed['action'].upper()} {removed['tool']}\n")


def _change_default(config):
    """Change the default action."""
    current = config.get("default", "ask")
    new_default = inquirer.select(
        message="Default action when no rule matches:",
        choices=ACTION_CHOICES,
        default=current,
    ).execute()
    config["default"] = new_default
    print(f"Default action set to: {new_default}\n")
