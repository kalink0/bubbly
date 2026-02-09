import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from exporter import BubblyExporter
from parsers.whatsapp_chat_export import WhatsAppChatExportParser
from parsers.telegram_desktop_chat_export import TelegramDesktopChatExportParser
from parsers.wire_messenger_backup import WireMessengerBackupParser
from utils import prepare_input_generic 


BUBBLY_VERSION = "0.1"

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
# Parser registry
# ----------------------
PARSERS = {
    "whatsapp_export": WhatsAppChatExportParser,
    "telegram_desktop_export": TelegramDesktopChatExportParser,
    "wire_messenger_backup": WireMessengerBackupParser,
}

# ----------------------
# CLI
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
    if "parser_args" not in defaults and "extra_args" in config:
        defaults["parser_args"] = config["extra_args"]
    if defaults:
        parser.set_defaults(**defaults)


def parse_args():
    parser = argparse.ArgumentParser(description="Bubbly Launcher - Chat Export Viewer")
    parser.add_argument("--config", help="Path to JSON config file")
    parser.add_argument("--parser", help="Parser name")
    parser.add_argument("--input", help="Input file/folder/zip")
    parser.add_argument("--output", help="Output folder for HTML report")
    parser.add_argument("--creator", help="User generating the report")
    parser.add_argument("--case", help="Case number")
    parser.add_argument("--templates_folder", help="Path to templates folder")
    parser.add_argument("--parser_args", nargs="*", help="Parser-specific args as key=value pairs")
    parser.add_argument("--extra_args", nargs="*", help="Deprecated. Use --parser_args instead")
    parser.add_argument(
        "--show_parser_args",
        action="store_true",
        help="Show extra args supported by the selected parser and exit",
    )

    if len(sys.argv) == 1 or "-h" in sys.argv:
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
        parser_args = getattr(parser_class, "EXTRA_ARGS", {})
        print(f"Parser args for parser '{args.parser}':")
        if not parser_args:
            print(" (none)")
        else:
            for key, description in parser_args.items():
                print(f" - {key}: {description}")
        raise SystemExit(0)

    missing = [
        name
        for name in ("parser", "input", "output", "creator", "case", "templates_folder")
        if not getattr(args, name)
    ]
    if missing:
        parser.error(f"Missing required arguments: {', '.join(missing)}")
    return args

# ----------------------
# Parse key=value pairs
# ----------------------
def parse_extra_args(extra_args_list):
    kwargs = {}
    if isinstance(extra_args_list, dict):
        return dict(extra_args_list)
    if extra_args_list:
        for item in extra_args_list:
            if "=" in item:
                k, v = item.split("=", 1)
                # Convert true/false to bool
                if v.lower() == "true":
                    v = True
                elif v.lower() == "false":
                    v = False
                kwargs[k] = v
    return kwargs


# ----------------------
# Main
# ----------------------
def main():
    print_banner()
    args = parse_args()
    parser_class = PARSERS.get(args.parser)
    if not parser_class:
        raise ValueError(f"Unknown parser {args.parser}. Available: {list(PARSERS.keys())}")

    # Prepare input (zip/folder/file)
    input_path, media_folder = prepare_input_generic(args.input)

    # Parser-specific kwargs
    config_extra = {}
    if isinstance(getattr(args, "_config", None), dict):
        config_extra = parse_extra_args(args._config.get("parser_args") or args._config.get("extra_args"))
    cli_extra = parse_extra_args(args.parser_args or args.extra_args)
    extra_kwargs = {**config_extra, **cli_extra}

    # Add generic metadata
    extra_kwargs.update({
        "user": args.creator,
        "case": args.case,
        "chat_name": extra_kwargs.get("chat_name"),
    })

    # Initialize parser
    parser_instance = parser_class()

    # Parse messages
    messages, metadata = parser_instance.parse(input_path, media_folder, **extra_kwargs)

    # Export HTML
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_folder = Path(args.output) / f"bubbly_{timestamp}"
    safe_case = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(args.case)).strip("._-")
    if not safe_case:
        safe_case = "case"
    output_html_name = f"{safe_case}_report.html"
    exporter = BubblyExporter(messages, media_folder, output_folder, metadata, templates_folder=args.templates_folder)
    exporter.export_html(output_html_name=output_html_name)

if __name__ == "__main__":
    main()
