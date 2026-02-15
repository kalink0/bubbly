"""CLI argument and configuration helpers for the Bubbly launcher."""

import argparse
import json
import sys
from pathlib import Path

from .interactive_cli import run_interactive_wizard


def load_config(config_path):
    """Load JSON configuration from --config or fallback default_conf.json."""
    default_path = Path(__file__).resolve().parent.parent / "default_conf.json"
    if not config_path:
        if not default_path.is_file():
            return {}
        config_path = default_path
    path = Path(config_path)
    if not path.is_file():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    if path.suffix.lower() != ".json":
        raise ValueError("Config file must be a .json file")
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("Config file root must be a JSON object")
    return data


def apply_config(parser, config):
    """Apply supported config keys as argparse defaults."""
    if not config:
        return
    defaults = {}
    for key in (
        "parser",
        "input",
        "output",
        "creator",
        "case",
        "logo",
        "split_by_chat",
        "parser_args",
    ):
        if key in config:
            defaults[key] = config[key]
    if defaults:
        parser.set_defaults(**defaults)


def parse_parser_args(parser_args_list):
    """Parse parser-specific key=value pairs from CLI/config into a dictionary."""
    parsed_parser_args = {}
    if isinstance(parser_args_list, dict):
        return dict(parser_args_list)
    if parser_args_list:
        for item in parser_args_list:
            if "=" in item:
                key, value = item.split("=", 1)
                if value.lower() == "true":
                    value = True
                elif value.lower() == "false":
                    value = False
                parsed_parser_args[key] = value
    return parsed_parser_args


def parse_args(parsers):
    """Parse CLI arguments, merge config defaults, and validate required fields."""
    parser = argparse.ArgumentParser(description="Bubbly Launcher - Chat Export Viewer")
    parser.set_defaults(split_by_chat=True)
    parser.add_argument("-f", "--config", help="Path to JSON config file")
    parser.add_argument("-p", "--parser", help="Parser name")
    parser.add_argument("-i", "--input", help="Input file/folder/zip")
    parser.add_argument("-o", "--output", help="Output folder for HTML report")
    parser.add_argument("-u", "--creator", help="User generating the report")
    parser.add_argument("-k", "--case", help="Case number")
    parser.add_argument("--logo", help="Optional branding logo image path")
    parser.add_argument(
        "--no-split-by-chat",
        dest="split_by_chat",
        action="store_false",
        help="Generate one merged HTML instead of per-chat files",
    )
    parser.add_argument("-a", "--parser_args", nargs="*", help="Parser-specific args as key=value pairs")
    parser.add_argument(
        "-s",
        "--show_parser_args",
        action="store_true",
        help="Show parser args supported by the selected parser and exit",
    )
    parser.add_argument(
        "-m",
        "--interactive",
        action="store_true",
        help="Run interactive menu mode (guided setup)",
    )

    if "-h" in sys.argv:
        print("Available parsers:")
        for name in parsers.keys():
            print(f" - {name}")
        print()
        parser.print_help()
        raise SystemExit(0)

    partial_args, _ = parser.parse_known_args()
    config = load_config(partial_args.config)
    apply_config(parser, config)
    args = parser.parse_args()
    args._config = config

    if args.show_parser_args:
        if not args.parser:
            parser.error("--show_parser_args requires --parser")
        parser_class = parsers.get(args.parser)
        if not parser_class:
            parser.error(f"Unknown parser {args.parser}. Available: {list(parsers.keys())}")
        supported_parser_args = getattr(parser_class, "PARSER_ARGS", {})
        print(f"Parser args for parser '{args.parser}':")
        if not supported_parser_args:
            print(" (none)")
        else:
            for key, description in supported_parser_args.items():
                print(f" - {key}: {description}")
        raise SystemExit(0)

    if args.interactive or len(sys.argv) == 1:
        return run_interactive_wizard(parser, args, parsers, parse_parser_args)

    missing = [
        name
        for name in ("parser", "input", "output", "creator", "case")
        if not getattr(args, name)
    ]
    if missing:
        parser.error(f"Missing required arguments: {', '.join(missing)}")
    return args
