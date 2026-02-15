"""Tests for CLI/config argument handling utilities."""

import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from utils.cli_config import load_config, parse_args, parse_parser_args


class _DummyParser:
    PARSER_ARGS = {"foo": "Optional test parameter"}


class TestCliConfig(unittest.TestCase):
    """Tests for parse/load behavior of CLI config utilities."""

    def test_load_config_missing_file_raises(self):
        """Loading a missing config path should raise FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            load_config("does_not_exist.json")

    def test_load_config_non_json_raises(self):
        """Loading a non-JSON config path should raise ValueError."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "conf.txt"
            path.write_text("x", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_config(path)

    def test_load_config_root_not_object_raises(self):
        """Config root must be a JSON object."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "conf.json"
            path.write_text("[]", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_config(path)

    def test_parse_parser_args_bool_and_key_values(self):
        """Parser args should parse booleans and key-value pairs correctly."""
        result = parse_parser_args(["a=true", "b=false", "c=value"])
        self.assertEqual(True, result["a"])
        self.assertEqual(False, result["b"])
        self.assertEqual("value", result["c"])

    def test_parse_args_cli_overrides_config(self):
        """CLI args should override configured defaults for overlapping keys."""
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "conf.json"
            cfg = {
                "parser": "dummy",
                "input": "/cfg/input",
                "output": "/cfg/output",
                "creator": "CfgUser",
                "case": "CFG-1",
                "log_level": "error",
                "split_by_chat": True,
                "parser_args": {"foo": "cfg"},
            }
            cfg_path.write_text(json.dumps(cfg), encoding="utf-8")

            argv = [
                "prog",
                "--config", str(cfg_path),
                "--parser", "dummy",
                "--input", "/cli/input",
                "--output", "/cli/output",
                "--creator", "CliUser",
                "--case", "CLI-1",
                "--log-level", "warning",
                "--no-split-by-chat",
                "--parser_args", "foo=cli",
            ]
            with patch.object(sys, "argv", argv):
                args = parse_args({"dummy": _DummyParser})
            self.assertEqual("/cli/output", args.output)
            self.assertEqual("/cli/input", args.input)
            self.assertEqual("warning", args.log_level)
            self.assertFalse(args.split_by_chat)
            self.assertEqual(["foo=cli"], args.parser_args)

    def test_show_parser_args_requires_parser(self):
        """show_parser_args without parser should terminate with argparse error."""
        with patch.object(sys, "argv", ["prog", "--show_parser_args"]):
            with self.assertRaises(SystemExit):
                parse_args({"dummy": _DummyParser})

    def test_show_parser_args_unknown_parser(self):
        """Unknown parser with show_parser_args should fail via argparse."""
        with patch.object(sys, "argv", ["prog", "--show_parser_args", "--parser", "unknown"]):
            with self.assertRaises(SystemExit):
                parse_args({"dummy": _DummyParser})

    def test_show_parser_args_prints_and_exits(self):
        """Known parser should print parser args and exit cleanly."""
        out = io.StringIO()
        with patch.object(sys, "stdout", out):
            with patch.object(sys, "argv", ["prog", "--show_parser_args", "--parser", "dummy"]):
                with self.assertRaises(SystemExit) as ctx:
                    parse_args({"dummy": _DummyParser})
        self.assertEqual(0, ctx.exception.code)
        self.assertIn("Parser args for parser 'dummy'", out.getvalue())

    def test_interactive_calls_banner_printer(self):
        """Interactive mode should call banner printer before wizard prompt."""
        banner_calls = []

        def _banner():
            banner_calls.append(True)

        with patch("utils.cli_config.run_interactive_wizard") as wizard:
            wizard.side_effect = lambda parser, args, parsers, parse_parser_args: args
            with patch.object(sys, "argv", ["prog", "--interactive"]):
                args = parse_args({"dummy": _DummyParser}, banner_printer=_banner)
        self.assertTrue(getattr(args, "_banner_shown", False))
        self.assertEqual(1, len(banner_calls))


if __name__ == "__main__":
    unittest.main()
