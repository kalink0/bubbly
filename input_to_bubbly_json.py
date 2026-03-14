"""Convert input message datasets into Bubbly-compatible generic JSON format."""

import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path


ALLOWED_MESSAGE_FIELDS = {
    "sender",
    "timestamp",
    "content",
    "media",
    "url",
    "is_owner",
    "chat",
}

REQUIRED_MESSAGE_FIELDS = {"sender", "timestamp", "content"}

ISO_TIMESTAMP_RE = re.compile(
    r"^(\\d{4})-(\\d{2})-(\\d{2})T(\\d{2}):(\\d{2}):(\\d{2})(Z|[+-]\\d{2}:\\d{2})?$"
)


def parse_mapping(mapping_items):
    """Parse TARGET=CSV_COLUMN mappings and validate required fields."""
    mapping = {}
    for item in mapping_items or []:
        if "=" not in item:
            raise ValueError(f"Invalid mapping '{item}'. Expected target=csv_column.")
        target, column = item.split("=", 1)
        target = target.strip()
        column = column.strip()
        if not target or not column:
            raise ValueError(f"Invalid mapping '{item}'. Empty target or column.")
        if target not in ALLOWED_MESSAGE_FIELDS:
            raise ValueError(
                f"Unsupported target field '{target}'. Allowed: {sorted(ALLOWED_MESSAGE_FIELDS)}"
            )
        mapping[target] = column

    missing = REQUIRED_MESSAGE_FIELDS - set(mapping.keys())
    if missing:
        raise ValueError(
            f"Missing required mapping(s): {sorted(missing)}. "
            "You must map sender, timestamp, and content."
        )
    return mapping


def parse_bool(value):
    """Convert common truthy string forms into a boolean value."""
    if value is None:
        return False
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "y", "t"}


def normalize_timestamp(value, fmt=None, timezone_hint=None):
    """Normalize timestamps into ISO 8601 strings."""
    if value is None:
        raise ValueError("Missing timestamp value")
    text = str(value).strip()
    if not text:
        raise ValueError("Empty timestamp value")

    if fmt:
        try:
            dt = datetime.strptime(text, fmt)
        except ValueError as exc:
            raise ValueError(
                f"Invalid timestamp '{text}'. Expected format: {fmt}"
            ) from exc

        if dt.tzinfo is None and timezone_hint:
            if timezone_hint == "utc":
                dt = dt.replace(tzinfo=timezone.utc)
            elif timezone_hint == "local":
                dt = dt.replace(tzinfo=datetime.now().astimezone().tzinfo)

        return dt.isoformat(timespec="seconds")

    if not ISO_TIMESTAMP_RE.match(text):
        raise ValueError(
            "Timestamp must be ISO 8601 (e.g. 2026-02-01T12:34:56) "
            "or provide a timestamp format."
        )
    return text


def build_messages(
    csv_path,
    mapping,
    delimiter=",",
    encoding="utf-8",
    strict=False,
    timestamp_format=None,
    timestamp_timezone=None,
):
    """Build normalized message dictionaries from CSV rows using field mapping."""
    messages = []
    skipped = 0
    skipped_rows = []
    with csv_path.open("r", encoding=encoding, newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        headers = reader.fieldnames or []
        missing_columns = sorted({column for column in mapping.values() if column not in headers})
        if missing_columns:
            raise ValueError(f"CSV is missing mapped column(s): {missing_columns}")

        for row_index, row in enumerate(reader, start=2):
            message = {}
            for target, column in mapping.items():
                raw_value = row.get(column, "")
                value = raw_value.strip() if isinstance(raw_value, str) else raw_value
                if target == "is_owner":
                    message[target] = parse_bool(value)
                elif target == "timestamp":
                    message[target] = normalize_timestamp(
                        value,
                        fmt=timestamp_format,
                        timezone_hint=timestamp_timezone,
                    )
                else:
                    message[target] = value

            missing_required_values = [
                field for field in REQUIRED_MESSAGE_FIELDS if not str(message.get(field, "")).strip()
            ]
            if missing_required_values:
                if strict:
                    raise ValueError(
                        f"Row {row_index}: missing required value(s) {missing_required_values}"
                    )
                skipped += 1
                skipped_rows.append((row_index, missing_required_values))
                continue

            messages.append(message)
    return messages, skipped, skipped_rows


def main():
    """Parse CLI args and write converted CSV content as Bubbly JSON."""
    parser = argparse.ArgumentParser(
        description="Convert a CSV file into Bubbly generic JSON format."
    )
    parser.add_argument("--csv", required=True, help="Path to input CSV file")
    parser.add_argument("--output", required=True, help="Path to output JSON file")
    parser.add_argument("--messenger", required=True, help="Messenger/platform value for metadata")
    parser.add_argument("--source", required=True, help="Source value for metadata")
    parser.add_argument("--chat_name", help="Optional chat name for top-level metadata")
    parser.add_argument(
        "--map",
        nargs="+",
        required=True,
        metavar="TARGET=CSV_COLUMN",
        help="Message field mappings, e.g. sender=person timestamp=ts content=body",
    )
    parser.add_argument("--delimiter", default=",", help="CSV delimiter (default: ,)")
    parser.add_argument("--encoding", default="utf-8", help="CSV encoding (default: utf-8)")
    parser.add_argument(
        "--timestamp_format",
        help=(
            "Optional timestamp format for CSV values "
            "(Python strptime, e.g. %d/%m/%Y %H:%M). "
            "If omitted, timestamp must already be ISO 8601."
        ),
    )
    parser.add_argument(
        "--timestamp_timezone",
        choices=["utc", "local"],
        help="Timezone to assume for naive timestamps (used with --timestamp_format).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail if any row misses required mapped values instead of skipping it",
    )

    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.is_file():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    mapping = parse_mapping(args.map)
    messages, skipped, skipped_rows = build_messages(
        csv_path=csv_path,
        mapping=mapping,
        delimiter=args.delimiter,
        encoding=args.encoding,
        strict=args.strict,
        timestamp_format=args.timestamp_format,
        timestamp_timezone=args.timestamp_timezone,
    )

    payload = {
        "source": args.source,
        "platform": args.messenger,
        "messages": messages,
    }
    if args.chat_name:
        payload["chat_name"] = args.chat_name

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    if skipped_rows:
        log_path = output_path.with_suffix(".skipped.log")
        with log_path.open("w", encoding="utf-8") as handle:
            for row_index, missing_fields in skipped_rows:
                handle.write(f"Row {row_index}: missing required values {missing_fields}\n")

    print(
        f"Wrote {len(messages)} message(s) to {output_path}. "
        f"Skipped rows: {skipped}."
    )


if __name__ == "__main__":
    main()
