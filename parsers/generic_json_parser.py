"""
Generic JSON Chat Export Parser

Created: 2026-02-10
Author: Kalink0
Description: Creates Bubbly JSON from a generic JSON schema.
"""

from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any
import json
import re


class GenericJsonParser:
    """
    Parser for generic JSON chat exports.
    """
    PARSER_ARGS = {
        "json_file": "Optional. JSON file name to load when input is a folder/zip.",
        "messages_key": "Optional. Key holding messages list (default: messages).",
        "metadata_key": "Optional. Key holding metadata dict (default: metadata).",
        "account_name": "Optional. Owner display name for is_owner detection.",
    }

    def parse(
        self,
        input_path: Path,
        media_folder: Path,
        account_name: Optional[str] = None,
        messages_key: Optional[str] = None,
        metadata_key: Optional[str] = None,
        **kwargs
    ) -> Tuple[List[Dict], Dict]:
        """Parse one generic JSON export into normalized messages and metadata."""
        input_path = Path(input_path)
        media_folder = Path(media_folder)

        json_path = self._resolve_json_path(input_path, messages_key, kwargs)
        with json_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)

        messages_raw, metadata_raw = self._extract_payload(
            data, messages_key=messages_key, metadata_key=metadata_key
        )

        messages: List[Dict] = []
        chat_name = (
            metadata_raw.get("chat_name")
            or kwargs.get("chat_name")
            or (json_path.stem if json_path.is_file() else None)
        )
        for msg in messages_raw:
            normalized = self._normalize_message(
                msg,
                chat_name=chat_name,
                account_name=account_name,
            )
            if normalized:
                messages.append(normalized)

        metadata = {
            "user": kwargs.get("user"),
            "case": kwargs.get("case"),
            "chat_name": chat_name,
            "source": metadata_raw.get("source") or "Generic JSON",
            "platform": metadata_raw.get("platform") or "generic",
        }

        return messages, metadata

    def resolve_json_paths(
        self,
        input_path: Path,
        json_file: Optional[str] = None,
    ) -> List[Path]:
        """Resolve all JSON input files for merge-mode processing."""
        input_path = Path(input_path)
        if input_path.is_file() and input_path.suffix.lower() == ".json":
            return [input_path]

        if input_path.is_dir():
            if json_file:
                candidate = input_path / json_file
                if candidate.is_file():
                    return [candidate]
                raise FileNotFoundError(f"JSON file not found: {candidate}")

            default_names = ["result.json", "chat.json", "messages.json"]
            found_defaults = [input_path / name for name in default_names if (input_path / name).is_file()]
            if found_defaults:
                return found_defaults

            json_files = sorted(input_path.glob("*.json"))
            if json_files:
                return json_files
            raise FileNotFoundError(f"No .json export found in {input_path}")

        raise ValueError(f"Unsupported input type: {input_path}")

    def _resolve_json_path(
        self,
        input_path: Path,
        messages_key: Optional[str],
        kwargs: Dict[str, Any],
    ) -> Path:
        if input_path.is_file() and input_path.suffix.lower() == ".json":
            return input_path

        if input_path.is_dir():
            preferred = kwargs.get("json_file")
            if preferred:
                candidate = input_path / preferred
                if candidate.is_file():
                    return candidate
                raise FileNotFoundError(f"JSON file not found: {candidate}")

            default_names = ["result.json", "chat.json", "messages.json"]
            for name in default_names:
                candidate = input_path / name
                if candidate.is_file():
                    return candidate

            json_files = list(input_path.glob("*.json"))
            if len(json_files) == 1:
                return json_files[0]
            if json_files:
                raise FileNotFoundError(
                    "Multiple .json files found; set json_file to select one"
                )
            raise FileNotFoundError(f"No .json export found in {input_path}")

        raise ValueError(f"Unsupported input type: {input_path}")

    def _extract_payload(
        self,
        data: Any,
        messages_key: Optional[str],
        metadata_key: Optional[str],
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        if isinstance(data, list):
            return data, {}

        if not isinstance(data, dict):
            raise ValueError("Invalid JSON export: expected list or object")

        key = messages_key or "messages"
        messages = data.get(key)
        if messages is None and "data" in data:
            messages = data.get("data")

        if messages is None or not isinstance(messages, list):
            raise ValueError(f"Invalid JSON export: '{key}' is not a list")

        meta_key = metadata_key or "metadata"
        metadata = data.get(meta_key) if isinstance(data.get(meta_key), dict) else {}
        if "chat_name" in data and "chat_name" not in metadata:
            metadata["chat_name"] = data.get("chat_name")
        if "source" in data and "source" not in metadata:
            metadata["source"] = data.get("source")
        if "platform" in data and "platform" not in metadata:
            metadata["platform"] = data.get("platform")

        return messages, metadata

    def _normalize_message(
        self,
        msg: Any,
        chat_name: Optional[str],
        account_name: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        if not isinstance(msg, dict):
            return None

        sender = msg.get("sender") or msg.get("from") or msg.get("author") or msg.get("user")
        sender = sender if sender is not None else "Unknown"

        raw_timestamp = msg.get("timestamp") or msg.get("time") or msg.get("date") or ""
        timestamp = self._normalize_timestamp(raw_timestamp)
        content = msg.get("content") or msg.get("text") or msg.get("message") or ""
        media = self._normalize_media(msg.get("media") or msg.get("file") or msg.get("attachment"))
        url = msg.get("url")

        is_owner = msg.get("is_owner")
        if is_owner is None and account_name:
            is_owner = sender == account_name

        return {
            "timestamp": timestamp,
            "sender": sender,
            "content": content,
            "media": media,
            "url": url,
            "is_owner": bool(is_owner),
            "chat": msg.get("chat") or msg.get("chat_name") or chat_name,
        }

    def _normalize_timestamp(self, value: Any) -> str:
        if not isinstance(value, str):
            raise ValueError("Invalid timestamp: expected ISO 8601 string")
        text = value.strip()
        if not text:
            raise ValueError("Invalid timestamp: empty value")

        # Required format: ISO 8601, timezone optional
        # Examples: 2026-02-01T12:34:56, 2026-02-01T12:34:56Z, 2026-02-01T12:34:56+02:00
        match = re.match(
            r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(Z|[+-]\d{2}:\d{2})?$",
            text,
        )
        if not match:
            raise ValueError(
                "Invalid timestamp format. Expected ISO 8601, "
                "e.g. 2026-02-01T12:34:56 or 2026-02-01T12:34:56Z"
            )
        return text

    def _normalize_media(self, media: Any) -> Optional[str]:
        if not media:
            return None
        if isinstance(media, str):
            return None if "File not included" in media else media
        if isinstance(media, dict):
            path = media.get("path") or media.get("file") or media.get("name")
            if isinstance(path, str):
                return None if "File not included" in path else path
        if isinstance(media, list):
            for item in media:
                if isinstance(item, str):
                    return None if "File not included" in item else item
                if isinstance(item, dict):
                    path = item.get("path") or item.get("file") or item.get("name")
                    if isinstance(path, str):
                        return None if "File not included" in path else path
        return None
