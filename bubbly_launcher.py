"""CLI launcher for parsing chat exports and generating Bubbly reports."""

import re
import sys
from datetime import datetime
from pathlib import Path

from bubbly_version import BUBBLY_VERSION
from exporter import BubblyExporter
from parsers.generic_json_parser import GenericJsonParser
from parsers.romeo_android_db import RomeoAndroidDbParser
from parsers.telegram_desktop_chat_export import TelegramDesktopChatExportParser
from parsers.threema_messenger_backup import ThreemaMessengerBackupParser
from parsers.wire_messenger_backup import WireMessengerBackupParser
from parsers.whatsapp_chat_export import WhatsAppChatExportParser
from utils import (
    RunLogger,
    collect_processed_files,
    export_split_by_chat,
    normalize_user_path,
    parse_args,
    parse_parser_args,
    prepare_input_generic,
    print_cli_summary,
    write_fallback_exception_log,
)


PARSERS = {
    "whatsapp_export": WhatsAppChatExportParser,
    "telegram_desktop_export": TelegramDesktopChatExportParser,
    "wire_messenger_backup": WireMessengerBackupParser,
    "threema_messenger_backup": ThreemaMessengerBackupParser,
    "generic_json": GenericJsonParser,
    "romeo_android_db": RomeoAndroidDbParser,
}


def print_banner():
    """Print the colored Bubbly CLI banner."""
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


def main():
    """Run the end-to-end launcher flow: parse, export, and log execution."""
    output_base = None
    try:
        args = parse_args(PARSERS, banner_printer=print_banner)
        args.output = str(normalize_user_path(args.output, must_exist=False))
        if getattr(args, "logo", None):
            args.logo = str(normalize_user_path(args.logo, must_exist=True))
        parser_class = PARSERS.get(args.parser)
        if not parser_class:
            raise ValueError(f"Unknown parser {args.parser}. Available: {list(PARSERS.keys())}")

        if parser_class is RomeoAndroidDbParser:
            raw_input = normalize_user_path(args.input, must_exist=True)
            if raw_input.is_file() and raw_input.suffix.lower() in {".zip", ".wbu"}:
                input_path, media_folder = prepare_input_generic(args.input)
            else:
                input_path = raw_input
                media_folder = input_path.parent if input_path.is_file() else input_path
        else:
            input_path, media_folder = prepare_input_generic(args.input)

        config_parser_args = {}
        if isinstance(getattr(args, "_config", None), dict):
            config_parser_args = parse_parser_args(args._config.get("parser_args"))
        cli_parser_args = parse_parser_args(args.parser_args)
        parser_kwargs = {**config_parser_args, **cli_parser_args}
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

        with RunLogger(
            output_base=output_base,
            args=args,
            config_parser_args=config_parser_args,
            cli_parser_args=cli_parser_args,
            parser_kwargs=parser_kwargs,
            log_level=args.log_level,
        ):
            if not getattr(args, "_banner_shown", False):
                print_banner()
            parser_instance = parser_class()

            if parser_class is GenericJsonParser:
                json_file = parser_kwargs.get("json_file")
                json_paths = parser_instance.resolve_json_paths(input_path, json_file=json_file)
                processed_files = collect_processed_files(args.parser, input_path, json_paths=json_paths)
                print(f"Processed source files ({len(processed_files)}):")
                for file_path in processed_files:
                    print(f" - {file_path}")
                messages_all = []
                metadata_all = None

                for json_path in json_paths:
                    run_kwargs = dict(parser_kwargs)
                    messages, metadata = parser_instance.parse(
                        json_path,
                        media_folder=media_folder,
                        **run_kwargs,
                    )
                    messages_all.extend(messages)
                    if metadata_all is None:
                        metadata_all = metadata

                if metadata_all is None:
                    raise ValueError("No JSON messages found to export")

                metadata_all = dict(metadata_all)
                if len(json_paths) > 1 and not args.split_by_chat:
                    metadata_all["chat_name"] = "Multiple chats"
            else:
                processed_files = collect_processed_files(args.parser, input_path)
                print(f"Processed source files ({len(processed_files)}):")
                for file_path in processed_files:
                    print(f" - {file_path}")
                messages_all, metadata_all = parser_instance.parse(
                    input_path,
                    media_folder=media_folder,
                    **parser_kwargs,
                )

            output_folder = output_base
            if args.split_by_chat:
                export_split_by_chat(
                    messages_all,
                    metadata_all,
                    media_folder,
                    output_folder,
                    args.logo,
                    safe_case,
                )
            else:
                output_html_name = f"{safe_case}_report.html"
                exporter = BubblyExporter(
                    messages_all,
                    media_folder,
                    output_folder,
                    metadata_all,
                    logo_path=args.logo,
                )
                exporter.export_html(output_html_name=output_html_name)

            print_cli_summary(messages_all, metadata_all)
    except SystemExit:
        raise
    except Exception as exc:
        fallback_base = (output_base / "log") if output_base is not None else None
        log_path = write_fallback_exception_log(exc, output_base=fallback_base)
        print(f"ERROR: {exc}", file=sys.stderr)
        print(f"Error log: {log_path}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
