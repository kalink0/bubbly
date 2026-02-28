"""Helpers for collecting parser-specific processed source files."""

import re
from pathlib import Path

_ROMEO_DB_PATTERN = re.compile(r"^planetromeo-room\.db\.\d+$")


def collect_processed_files(parser_name, input_path, json_paths=None):
    """Return a parser-specific list of source files used for processing."""
    root = Path(input_path)
    if parser_name == "generic_json":
        return [str(Path(path)) for path in (json_paths or [])]
    if parser_name == "whatsapp_export":
        return [str(path) for path in sorted(root.glob("*.txt"))]
    if parser_name == "telegram_desktop_export":
        preferred = root / "result.json"
        if preferred.is_file():
            return [str(preferred)]
        return [str(path) for path in sorted(root.glob("*.json"))]
    if parser_name == "threema_messenger_backup":
        files = []
        for pattern in ("contacts.csv", "groups.csv", "message_*.csv", "group_message_*.csv"):
            if "*" in pattern:
                files.extend(sorted(root.glob(pattern)))
            else:
                candidate = root / pattern
                if candidate.is_file():
                    files.append(candidate)
        return [str(path) for path in files]
    if parser_name == "wire_messenger_backup":
        files = []
        for pattern in ("messages_*.binpb", "conversations_*.binpb", "users_*.binpb"):
            files.extend(sorted(root.glob(pattern)))
        return [str(path) for path in files]
    if parser_name == "romeo_android_db":
        if root.is_file():
            return [str(root)]
        files = [
            path
            for path in sorted(root.iterdir())
            if path.is_file() and _ROMEO_DB_PATTERN.fullmatch(path.name)
        ]
        return [str(path) for path in files]
    return [str(root)]
