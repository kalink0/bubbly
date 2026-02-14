import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from exporter import BubblyExporter
from bubbly_version import BUBBLY_VERSION
from parsers.whatsapp_chat_export import WhatsAppChatExportParser
from parsers.telegram_desktop_chat_export import TelegramDesktopChatExportParser
from parsers.wire_messenger_backup import WireMessengerBackupParser
from parsers.threema_messenger_backup import ThreemaMessengerBackupParser
from parsers.generic_json_parser import GenericJsonParser
from utils import normalize_user_path, prepare_input_generic, run_interactive_wizard

# ----------------------
# Parser registry
# ----------------------
PARSERS = {
    "whatsapp_export": WhatsAppChatExportParser,
    "telegram_desktop_export": TelegramDesktopChatExportParser,
    "wire_messenger_backup": WireMessengerBackupParser,
    "threema_messenger_backup": ThreemaMessengerBackupParser,
    "generic_json": GenericJsonParser,
}

# ----------------------
# Printing the CLI banner
# ----------------------
def print_banner():
    width = 54
    inner_width = width - 2
    bubble_pattern = ("o O 0   " * ((inner_width // 7) + 1))[:inner_width]
    blue = "\033[34m"
    reset = "\033[0m"
    banner = "\n".join([
        blue + "+" + "-" * inner_width + "+" + reset,
        blue + "|" + bubble_pattern + "|" + reset,
        blue + "|" + "B U B B L Y ".center(inner_width) + "|" + reset,
        blue + "|" + f"v{BUBBLY_VERSION}".center(inner_width) + "|" + reset,
        blue + "|" + bubble_pattern + "|" + reset,
        blue + "+" + "-" * inner_width + "+" + reset,
    ])
    print(banner)


# ----------------------
# Config Handling
# ----------------------
def load_config(config_path):
    default_path = Path(__file__).resolve().parent / "default_conf.json"
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
    if not config:
        return
    defaults = {}
    for key in (
        "parser",
        "input",
        "output",
        "creator",
        "case",
        "templates_folder",
        "parser_args",
    ):
        if key in config:
            defaults[key] = config[key]
    if defaults:
        parser.set_defaults(**defaults)

# ----------------------
# Config Handling
# ----------------------
def parse_args():
    parser = argparse.ArgumentParser(description="Bubbly Launcher - Chat Export Viewer")
    parser.add_argument("-f", "--config", help="Path to JSON config file")
    parser.add_argument("-p", "--parser", help="Parser name")
    parser.add_argument("-i", "--input", help="Input file/folder/zip")
    parser.add_argument("-o", "--output", help="Output folder for HTML report")
    parser.add_argument("-u", "--creator", help="User generating the report")
    parser.add_argument("-k", "--case", help="Case number")
    parser.add_argument("-t", "--templates_folder", help="Path to templates folder")
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
        for name in PARSERS.keys():
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
        parser_class = PARSERS.get(args.parser)
        if not parser_class:
            parser.error(f"Unknown parser {args.parser}. Available: {list(PARSERS.keys())}")
        supported_parser_args = getattr(parser_class, "PARSER_ARGS", {})
        print(f"Parser args for parser '{args.parser}':")
        if not supported_parser_args:
            print(" (none)")
        else:
            for key, description in supported_parser_args.items():
                print(f" - {key}: {description}")
        raise SystemExit(0)

    if args.interactive or len(sys.argv) == 1:
        return run_interactive_wizard(parser, args, PARSERS, parse_parser_args)

    missing = [
        name
        for name in ("parser", "input", "output", "creator", "case", "templates_folder")
        if not getattr(args, name)
    ]
    if missing:
        parser.error(f"Missing required arguments: {', '.join(missing)}")
    return args

# ----------------------
# Parse key=value pairs for parser arguments
# ----------------------
def parse_parser_args(parser_args_list):
    parsed_parser_args = {}
    if isinstance(parser_args_list, dict):
        return dict(parser_args_list)
    if parser_args_list:
        for item in parser_args_list:
            if "=" in item:
                k, v = item.split("=", 1)
                # Convert true/false to bool
                if v.lower() == "true":
                    v = True
                elif v.lower() == "false":
                    v = False
                parsed_parser_args[k] = v
    return parsed_parser_args


# ----------------------
# Main
# ----------------------
def main():
    print_banner()
    args = parse_args()
    args.output = str(normalize_user_path(args.output, must_exist=False))
    args.templates_folder = str(normalize_user_path(args.templates_folder, must_exist=False))
    parser_class = PARSERS.get(args.parser)
    if not parser_class:
        raise ValueError(f"Unknown parser {args.parser}. Available: {list(PARSERS.keys())}")

    # Prepare input (zip/folder/file)
    input_path, media_folder = prepare_input_generic(args.input)

    # Parser-specific kwargs
    config_parser_args = {}
    if isinstance(getattr(args, "_config", None), dict):
        config_parser_args = parse_parser_args(args._config.get("parser_args"))
    cli_parser_args = parse_parser_args(args.parser_args)
    parser_kwargs = {**config_parser_args, **cli_parser_args}

    # Add generic metadata
    parser_kwargs.update({
        "user": args.creator,
        "case": args.case,
        "chat_name": parser_kwargs.get("chat_name"),
    })

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_base = Path(args.output) / f"bubbly_{timestamp}"
    safe_case = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(args.case)).strip("._-")
    if not safe_case:
        safe_case = "case"

    # Initialize parser
    parser_instance = parser_class()

    # A few steps to do specifically for the generic JSON parser
    if parser_class is GenericJsonParser:
        json_file = parser_kwargs.get("json_file")
        json_paths = parser_instance.resolve_json_paths(input_path, json_file=json_file)

        combined_messages = []
        combined_metadata = None
        any_group_chat = False

        for json_path in json_paths:
            run_kwargs = dict(parser_kwargs)

            messages, metadata = parser_instance.parse(json_path, media_folder, **run_kwargs)
            combined_messages.extend(messages)
            any_group_chat = any_group_chat or bool(metadata.get("is_group_chat"))
            if combined_metadata is None:
                combined_metadata = metadata

        if combined_metadata is None:
            raise ValueError("No JSON messages found to export")

        if len(json_paths) > 1:
            combined_metadata = dict(combined_metadata)
            combined_metadata["chat_name"] = "Multiple chats"
            combined_metadata["is_group_chat"] = any_group_chat

        output_folder = output_base
        output_html_name = f"{safe_case}_report.html"
        exporter = BubblyExporter(
            combined_messages,
            media_folder,
            output_folder,
            combined_metadata,
            templates_folder=args.templates_folder,
        )
        exporter.export_html(output_html_name=output_html_name)
   
    else:
        # Parsing and exporting for all other parsers
        messages, metadata = parser_instance.parse(input_path, media_folder, **parser_kwargs)

        output_folder = output_base
        output_html_name = f"{safe_case}_report.html"
        exporter = BubblyExporter(messages, media_folder, output_folder, metadata, templates_folder=args.templates_folder)
        exporter.export_html(output_html_name=output_html_name)

if __name__ == "__main__":
    main()
