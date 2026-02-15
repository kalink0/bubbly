"""Convert CSV message datasets into Bubbly-compatible generic JSON format."""

import argparse
import csv
import json
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


def build_messages(csv_path, mapping, delimiter=",", encoding="utf-8", strict=False):
    """Build normalized message dictionaries from CSV rows using field mapping."""
    messages = []
    skipped = 0
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
                continue

            messages.append(message)
    return messages, skipped


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
        "--strict",
        action="store_true",
        help="Fail if any row misses required mapped values instead of skipping it",
    )

    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.is_file():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    mapping = parse_mapping(args.map)
    messages, skipped = build_messages(
        csv_path=csv_path,
        mapping=mapping,
        delimiter=args.delimiter,
        encoding=args.encoding,
        strict=args.strict,
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

    print(
        f"Wrote {len(messages)} message(s) to {output_path}. "
        f"Skipped rows: {skipped}."
    )


if __name__ == "__main__":
    main()
