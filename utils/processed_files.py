"""Helpers for collecting parser-specific processed source files."""

from pathlib import Path


def _looks_like_sqlite(path: Path):
    try:
        with path.open("rb") as handle:
            header = handle.read(16)
    except OSError:
        return False
    return header == b"SQLite format 3\x00"


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
        files = []
        for pattern in ("*.db", "*.sqlite", "*.sqlite3"):
            files.extend(sorted(root.glob(pattern)))
        for path in sorted(root.iterdir()):
            if not path.is_file():
                continue
            if path in files:
                continue
            if _looks_like_sqlite(path):
                files.append(path)
        return [str(path) for path in files]
    return [str(root)]
