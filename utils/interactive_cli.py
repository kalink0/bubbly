import glob
import os
from contextlib import contextmanager
from pathlib import Path

try:
    import readline
except ImportError:
    readline = None


def _coerce_arg_value(value):
    if isinstance(value, str):
        lower = value.lower()
        if lower == "true":
            return True
        if lower == "false":
            return False
    return value


def _path_completer(text, state):
    expanded = os.path.expanduser(text or "")
    matches = []
    for value in sorted(glob.glob(f"{expanded}*")):
        candidate = Path(value)
        if candidate.is_dir():
            value = f"{value}/"
        if text.startswith("~"):
            home = str(Path.home())
            if value.startswith(home):
                value = value.replace(home, "~", 1)
        matches.append(value)
    if state < len(matches):
        return matches[state]
    return None


@contextmanager
def _path_completion_enabled():
    if readline is None:
        yield
        return
    old_completer = readline.get_completer()
    old_delims = readline.get_completer_delims()
    old_bind = readline.parse_and_bind
    try:
        readline.set_completer_delims(" \t\n;")
        readline.set_completer(_path_completer)
        readline.parse_and_bind("tab: complete")
        yield
    finally:
        readline.set_completer(old_completer)
        readline.set_completer_delims(old_delims)
        old_bind("tab: self-insert")


def _prompt_text(label, default=None, required=True, path_completion=False):
    while True:
        hint = f" [{default}]" if default not in (None, "") else ""
        if path_completion:
            with _path_completion_enabled():
                value = input(f"{label}{hint}: ").strip()
        else:
            value = input(f"{label}{hint}: ").strip()
        if value:
            return value
        if default not in (None, ""):
            return str(default)
        if not required:
            return ""
        print("Value is required.")


def _prompt_choice(label, options, default=None):
    option_list = list(options)
    option_set = set(option_list)
    index_map = {str(idx): value for idx, value in enumerate(option_list, start=1)}
    while True:
        hint = f" [{default}]" if default in option_set else ""
        value = input(f"{label}{hint}: ").strip()
        if not value and default in option_set:
            return default
        if value in index_map:
            return index_map[value]
        if value in option_set:
            return value
        numbered = ", ".join(f"{idx}={name}" for idx, name in index_map.items())
        print(f"Choose one of: {numbered}")


def _prompt_yes_no(label, default=False):
    yes_no_hint = "Y/n" if default else "y/N"
    while True:
        value = input(f"{label} [{yes_no_hint}]: ").strip().lower()
        if not value:
            return default
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print("Please answer y or n.")


def run_interactive_wizard(parser, args, parsers, parse_parser_args):
    print("Interactive mode: guided setup")
    print("Press Enter to accept defaults shown in [brackets].")
    print()
    print("Available parsers:")
    parser_names = list(parsers.keys())
    for idx, name in enumerate(parser_names, start=1):
        print(f" {idx}. {name}")
    print()

    args.parser = _prompt_choice("Parser", parser_names, default=args.parser)
    args.input = _prompt_text("Input path (file/folder/zip)", default=args.input, path_completion=True)
    args.output = _prompt_text("Output folder", default=args.output, path_completion=True)
    args.creator = _prompt_text("Creator", default=args.creator)
    args.case = _prompt_text("Case", default=args.case)
    args.templates_folder = _prompt_text("Templates folder", default=args.templates_folder, path_completion=True)
    args.split_by_chat = _prompt_yes_no(
        "Generate one HTML per chat (split by chat)?",
        default=bool(getattr(args, "split_by_chat", False)),
    )

    parser_class = parsers.get(args.parser)
    if not parser_class:
        parser.error(f"Unknown parser {args.parser}. Available: {list(parsers.keys())}")

    config_parser_args = {}
    if isinstance(getattr(args, "_config", None), dict):
        config_parser_args = parse_parser_args(args._config.get("parser_args"))
    current_parser_args = parse_parser_args(args.parser_args)
    merged_defaults = {**config_parser_args, **current_parser_args}

    parser_args = {}
    supported = getattr(parser_class, "PARSER_ARGS", {})
    if supported:
        print()
        print("Parser-specific arguments:")
        for key, description in supported.items():
            is_required = description.lower().startswith("required")
            if is_required:
                parser_args[key] = _prompt_text(
                    f" - {key} ({description})",
                    default=merged_defaults.get(key),
                    required=True,
                )
                parser_args[key] = _coerce_arg_value(parser_args[key])
                continue

            if key in merged_defaults:
                use_arg = _prompt_yes_no(f"Use {key}={merged_defaults.get(key)}?", default=True)
                if use_arg:
                    parser_args[key] = merged_defaults.get(key)
                    continue
            use_arg = _prompt_yes_no(f"Set optional '{key}'? ({description})", default=False)
            if use_arg:
                parser_args[key] = _prompt_text(
                    f"   value for {key}",
                    default=merged_defaults.get(key),
                    required=False,
                )
                parser_args[key] = _coerce_arg_value(parser_args[key])

    args.parser_args = parser_args
    return args
