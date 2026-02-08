import argparse
import json
from pathlib import Path
from bubbly.exporter import BubblyExporter
from bubbly.parsers.whatsapp_chat_export import WhatsAppChatExportParser
from bubbly.utils import prepare_input_generic 


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
    # Add future parsers here
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
        "extra_args",
    ):
        if key in config:
            defaults[key] = config[key]
    if defaults:
        parser.set_defaults(**defaults)


def parse_args():
    parser = argparse.ArgumentParser(description="Bubbly Launcher - Chat Export Viewer")
    parser.add_argument("--config", help="Path to JSON config file")
    parser.add_argument("--parser", help=f"Parser name. Available: {list(PARSERS.keys())}")
    parser.add_argument("--input", help="Input file/folder/zip")
    parser.add_argument("--output", help="Output folder for HTML report")
    parser.add_argument("--creator", help="User generating the report")
    parser.add_argument("--case", help="Case number")
    parser.add_argument("--templates_folder", help="Path to templates folder")
    parser.add_argument("--extra_args", nargs="*", help="Parser-specific args as key=value pairs")

    partial_args, _ = parser.parse_known_args()
    config = load_config(partial_args.config)
    apply_config(parser, config)
    args = parser.parse_args()
    args._config = config

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
        config_extra = parse_extra_args(args._config.get("extra_args"))
    cli_extra = parse_extra_args(args.extra_args)
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
    exporter = BubblyExporter(messages, media_folder, args.output, metadata, templates_folder=args.templates_folder)
    exporter.export_html()

if __name__ == "__main__":
    main()
