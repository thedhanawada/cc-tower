import argparse
import json
import os
import sys

from tower import __version__
from tower.config import DEFAULT_CONFIG, find_config_path, load_config
from tower.evaluator import evaluate_from_stdin
from tower.interactive import run_interactive_config


def cmd_init(args):
    """Generate default tower-rules.yml and install the hook."""
    # Write config
    config_path = os.path.join(os.getcwd(), "tower-rules.yml")
    if os.path.exists(config_path) and not args.force:
        print(f"Config already exists: {config_path}")
        print("Use --force to overwrite.")
        return 1

    with open(config_path, "w") as f:
        f.write(DEFAULT_CONFIG)
    print(f"Created {config_path}")

    # Install hook into .claude/settings.json
    settings_dir = os.path.join(os.getcwd(), ".claude")
    settings_path = os.path.join(settings_dir, "settings.json")

    os.makedirs(settings_dir, exist_ok=True)

    settings = {}
    if os.path.exists(settings_path):
        with open(settings_path) as f:
            settings = json.load(f)

    hook_entry = {
        "matcher": ".*",
        "hooks": [
            {
                "type": "command",
                "command": "tower evaluate",
            }
        ],
    }

    hooks = settings.setdefault("hooks", {})
    pre_tool_use = hooks.setdefault("PreToolUse", [])

    # Check if tower hook is already installed
    already_installed = any(
        any(h.get("command", "").startswith("tower") for h in entry.get("hooks", []))
        for entry in pre_tool_use
    )

    if not already_installed:
        pre_tool_use.append(hook_entry)
        with open(settings_path, "w") as f:
            json.dump(settings, f, indent=2)
        print(f"Installed PreToolUse hook in {settings_path}")
    else:
        print("Tower hook already installed in settings.")

    return 0


def cmd_status(args):
    """Show current rules summary and hook status."""
    config_path = find_config_path()
    if config_path is None:
        print("No tower-rules.yml found. Run 'tower init' to create one.")
        return 1

    print(f"Config: {config_path}")

    try:
        config = load_config(config_path)
    except (ValueError, FileNotFoundError) as e:
        print(f"Error loading config: {e}")
        return 1

    print(f"Default action: {config.get('default', 'ask')}")
    rules = config.get("rules", [])
    print(f"Rules: {len(rules)}")
    print()

    for i, rule in enumerate(rules):
        parts = [f"  {i + 1}. {rule['action'].upper():5s} {rule['tool']}"]
        if "command_pattern" in rule:
            parts.append(f"  command: /{rule['command_pattern']}/")
        if "path_pattern" in rule:
            parts.append(f"  path: {rule['path_pattern']}")
        if "reason" in rule:
            parts.append(f"  reason: {rule['reason']}")
        print("\n".join(parts))

    # Check hook installation
    print()
    settings_path = os.path.join(os.getcwd(), ".claude", "settings.json")
    if os.path.exists(settings_path):
        with open(settings_path) as f:
            settings = json.load(f)
        hooks = settings.get("hooks", {}).get("PreToolUse", [])
        tower_installed = any(
            any(
                h.get("command", "").startswith("tower") for h in e.get("hooks", [])
            )
            for e in hooks
        )
        if tower_installed:
            print("Hook: installed")
        else:
            print("Hook: NOT installed (run 'tower init')")
    else:
        print("Hook: NOT installed (no .claude/settings.json found)")

    return 0


def cmd_evaluate(args):
    """Evaluate a tool call from stdin."""
    evaluate_from_stdin()
    return 0


def cmd_config(args):
    """Launch interactive config editor."""
    return run_interactive_config()


def main():
    parser = argparse.ArgumentParser(
        prog="tower",
        description="Tower — Permission evaluation agent for Claude Code",
    )
    parser.add_argument(
        "--version", action="version", version=f"tower {__version__}"
    )

    subparsers = parser.add_subparsers(dest="command")

    # tower init
    init_parser = subparsers.add_parser("init", help="Initialize Tower config and hook")
    init_parser.add_argument(
        "--force", action="store_true", help="Overwrite existing config"
    )

    # tower status
    subparsers.add_parser("status", help="Show rules summary and hook status")

    # tower evaluate
    subparsers.add_parser(
        "evaluate", help="Evaluate a tool call from stdin (used by hook)"
    )

    # tower config
    subparsers.add_parser("config", help="Interactive config editor")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    commands = {
        "init": cmd_init,
        "status": cmd_status,
        "evaluate": cmd_evaluate,
        "config": cmd_config,
    }

    sys.exit(commands[args.command](args) or 0)


if __name__ == "__main__":
    main()
