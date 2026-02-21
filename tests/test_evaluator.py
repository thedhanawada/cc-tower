import json
import pytest

from tower.rules import match_rule, evaluate_rules, _expand_braces
from tower.evaluator import evaluate


SAMPLE_CONFIG = {
    "version": 1,
    "default": "ask",
    "rules": [
        {"tool": "Read", "action": "allow"},
        {"tool": "Glob", "action": "allow"},
        {"tool": "Grep", "action": "allow"},
        {
            "tool": "Edit",
            "path_pattern": "/home/user/myproject/**",
            "action": "allow",
        },
        {
            "tool": "Bash",
            "command_pattern": "^(ls|cat|git status|git diff|npm test|pytest).*",
            "action": "allow",
        },
        {
            "tool": "Bash",
            "command_pattern": "rm -rf|git push --force|DROP TABLE",
            "action": "deny",
            "reason": "Destructive command blocked by Tower",
        },
        {
            "tool": "Write",
            "path_pattern": "**/*.{py,js,ts,json,yml,yaml,md}",
            "action": "allow",
        },
    ],
}


class TestMatchRule:
    def test_simple_tool_match(self):
        rule = {"tool": "Read", "action": "allow"}
        assert match_rule(rule, "Read", {"file_path": "/tmp/test.txt"})

    def test_tool_no_match(self):
        rule = {"tool": "Read", "action": "allow"}
        assert not match_rule(rule, "Write", {"file_path": "/tmp/test.txt"})

    def test_command_pattern_match(self):
        rule = {
            "tool": "Bash",
            "command_pattern": "^(ls|git status).*",
            "action": "allow",
        }
        assert match_rule(rule, "Bash", {"command": "ls -la"})
        assert match_rule(rule, "Bash", {"command": "git status"})
        assert not match_rule(rule, "Bash", {"command": "rm -rf /"})

    def test_command_pattern_deny(self):
        rule = {
            "tool": "Bash",
            "command_pattern": "rm -rf|git push --force",
            "action": "deny",
        }
        assert match_rule(rule, "Bash", {"command": "rm -rf /tmp"})
        assert match_rule(rule, "Bash", {"command": "git push --force origin main"})
        assert not match_rule(rule, "Bash", {"command": "git push origin main"})

    def test_path_pattern_match(self):
        rule = {
            "tool": "Edit",
            "path_pattern": "/home/user/myproject/**",
            "action": "allow",
        }
        assert match_rule(
            rule, "Edit", {"file_path": "/home/user/myproject/src/main.py"}
        )
        assert not match_rule(
            rule, "Edit", {"file_path": "/home/other/file.py"}
        )

    def test_path_pattern_with_braces(self):
        rule = {
            "tool": "Write",
            "path_pattern": "**/*.{py,js}",
            "action": "allow",
        }
        assert match_rule(rule, "Write", {"file_path": "/tmp/test.py"})
        assert match_rule(rule, "Write", {"file_path": "/tmp/test.js"})
        assert not match_rule(rule, "Write", {"file_path": "/tmp/test.rb"})


class TestExpandBraces:
    def test_no_braces(self):
        assert _expand_braces("**/*.py") == ["**/*.py"]

    def test_simple_braces(self):
        result = _expand_braces("**/*.{py,js}")
        assert set(result) == {"**/*.py", "**/*.js"}

    def test_multiple_alternatives(self):
        result = _expand_braces("**/*.{py,js,ts}")
        assert set(result) == {"**/*.py", "**/*.js", "**/*.ts"}


class TestEvaluateRules:
    def test_allow_read(self):
        action, reason = evaluate_rules(
            SAMPLE_CONFIG, "Read", {"file_path": "/tmp/test.txt"}
        )
        assert action == "allow"

    def test_allow_glob(self):
        action, reason = evaluate_rules(
            SAMPLE_CONFIG, "Glob", {"pattern": "**/*.py"}
        )
        assert action == "allow"

    def test_allow_safe_bash(self):
        action, reason = evaluate_rules(
            SAMPLE_CONFIG, "Bash", {"command": "git status"}
        )
        assert action == "allow"

    def test_deny_destructive_bash(self):
        action, reason = evaluate_rules(
            SAMPLE_CONFIG, "Bash", {"command": "rm -rf /"}
        )
        # The safe bash rule matches first because "rm -rf" doesn't match ^(ls|cat|...)
        # and then the deny rule matches
        assert action == "deny"
        assert "Destructive" in reason

    def test_allow_write_py(self):
        action, reason = evaluate_rules(
            SAMPLE_CONFIG, "Write", {"file_path": "/tmp/main.py"}
        )
        assert action == "allow"

    def test_default_for_unknown_tool(self):
        action, reason = evaluate_rules(
            SAMPLE_CONFIG, "UnknownTool", {"some": "input"}
        )
        assert action == "ask"
        assert "default" in reason

    def test_allow_edit_in_project(self):
        action, reason = evaluate_rules(
            SAMPLE_CONFIG, "Edit", {"file_path": "/home/user/myproject/src/app.py"}
        )
        assert action == "allow"

    def test_ask_edit_outside_project(self):
        action, reason = evaluate_rules(
            SAMPLE_CONFIG, "Edit", {"file_path": "/home/other/app.py"}
        )
        assert action == "ask"


class TestEvaluateFunction:
    def test_evaluate_with_config(self):
        action, reason = evaluate("Read", {"file_path": "/tmp/x"}, config=SAMPLE_CONFIG)
        assert action == "allow"

    def test_evaluate_deny(self):
        action, reason = evaluate(
            "Bash", {"command": "DROP TABLE users"}, config=SAMPLE_CONFIG
        )
        assert action == "deny"
