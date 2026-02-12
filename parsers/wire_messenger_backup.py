"""
Wire Messenger Backup Parser

Parses Wire Messenger unencrypted backup exports containing .binpb protobuf files.
Encrypted backups are not supported at the moment.
The backup zip may include extra bytes before the ZIP header; this is
handled in utils.prepare_input_generic.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from datetime import datetime, timezone
import base64
import json


class WireMessengerBackupParser:
    """
    Parser for Wire Messenger unencrypted backups (.binpb protobuf files).
    """
    PARSER_ARGS = {
        "chat_name": "Optional. Overrides chat name in report header.",
    }

    def parse(
        self,
        input_folder: Path,
        media_folder: Path,
        **kwargs
    ) -> Tuple[List[Dict], Dict]:
        input_folder = Path(input_folder)
        media_folder = Path(media_folder)

        account_id = self._find_account_id(input_folder)
        conversations = self._load_wire_objects(input_folder, "conversations_*.binpb", "2")
        messages = self._load_wire_objects(input_folder, "messages_*.binpb", "3")
        users = self._load_wire_objects(input_folder, "users_*.binpb", "4")

        user_map = self._build_user_map(users)
        owner_name = user_map.get(account_id) if account_id else None
        conv_map = self._build_conversation_map(conversations)

        parsed_messages: List[Dict] = []
        for msg in messages:
            sender_id = self._normalize_id(msg.get("3"))
            conversation_id = self._normalize_id(msg.get("5"))
            chat_name = conv_map.get(conversation_id) or kwargs.get("chat_name") or conversation_id or "Chat"

            timestamp_ms = msg.get("2")
            timestamp = self._format_timestamp(timestamp_ms)

            content = self._extract_text(msg.get("6"))
            media = self._extract_media(msg.get("7"), media_folder)

            if not content and media:
                content = "[media]"

            parsed_messages.append({
                "timestamp": timestamp,
                "sender": user_map.get(sender_id, sender_id or "Unknown"),
                "content": content,
                "media": media,
                "url": None,
                "is_owner": bool(account_id and sender_id == account_id),
                "chat": chat_name,
            })

        metadata = {
            "user": kwargs.get("user"),
            "case": kwargs.get("case"),
            "chat_name": kwargs.get("chat_name"),
            "source": "Wire Messenger",
            "platform": "desktop",
            "is_group_chat": None,
            "wire_account_name": owner_name,
        }

        return parsed_messages, metadata

    # ----------------------
    # Loading helpers
    # ----------------------
    def _load_wire_objects(self, root: Path, pattern: str, field_key: str) -> List[Dict[str, Any]]:
        objects: List[Dict[str, Any]] = []
        for path in sorted(root.glob(pattern)):
            data = self._load_binpb_or_json(path)
            if not isinstance(data, dict):
                continue
            # Header is typically at field "1", list payload follows in field_key.
            value = data.get(field_key)
            if isinstance(value, list):
                objects.extend([item for item in value if isinstance(item, dict)])
            elif isinstance(value, dict):
                objects.append(value)
        return objects

    def _load_binpb_or_json(self, path: Path) -> Any:
        if path.suffix.lower() == ".json":
            with path.open("r", encoding="utf-8") as handle:
                return json.load(handle)
        data = path.read_bytes()
        return decode_protobuf_to_dict(data)

    def _find_account_id(self, root: Path) -> str:
        for pattern in ("messages_*.binpb", "conversations_*.binpb", "users_*.binpb"):
            for path in sorted(root.glob(pattern)):
                data = self._load_binpb_or_json(path)
                if not isinstance(data, dict):
                    continue
                header = data.get("1")
                if isinstance(header, dict):
                    account_id = self._normalize_id(header.get("3"))
                    if account_id:
                        return account_id
        return ""

    # ----------------------
    # Field extraction
    # ----------------------
    def _build_user_map(self, users: Iterable[Dict[str, Any]]) -> Dict[str, str]:
        mapping: Dict[str, str] = {}
        for entry in users:
            user_id = self._normalize_id(entry.get("1"))
            if not user_id:
                continue
            display = entry.get("2") or entry.get("3") or user_id
            mapping[user_id] = str(display)
        return mapping

    def _build_conversation_map(self, conversations: Iterable[Dict[str, Any]]) -> Dict[str, str]:
        mapping: Dict[str, str] = {}
        for entry in conversations:
            conv_id = self._normalize_id(entry.get("1"))
            if not conv_id:
                continue
            name = entry.get("2")
            if isinstance(name, str) and name.strip() and name.strip() != "_":
                mapping[conv_id] = name.strip()
            else:
                mapping[conv_id] = conv_id
        return mapping

    def _normalize_id(self, id_obj: Any) -> str:
        if isinstance(id_obj, dict):
            left = id_obj.get("1")
            right = id_obj.get("2")
            left_text = str(left) if isinstance(left, str) else ""
            right_text = str(right) if isinstance(right, str) else ""
            return left_text or right_text
        if id_obj is None:
            return ""
        return str(id_obj)

    def _extract_text(self, content_obj: Any) -> str:
        if isinstance(content_obj, dict):
            value = content_obj.get("1")
            return self._decode_base64_text(value)
        if isinstance(content_obj, str):
            return self._decode_base64_text(content_obj)
        return ""

    def _decode_base64_text(self, value: Any) -> str:
        if value is None:
            return ""
        text = str(value)
        if text.startswith("base64:"):
            payload = text.split(":", 1)[1]
        elif text.startswith("base64"):
            payload = text[len("base64"):].lstrip(":")
        else:
            return text
        try:
            decoded = base64.b64decode(payload, validate=False)
            return decoded.decode("utf-8", errors="replace")
        except Exception:
            return text

    def _extract_media(self, media_obj: Any, media_folder: Path) -> Optional[str]:
        if not isinstance(media_obj, dict):
            return None
        filename = media_obj.get("3")
        alt_id = media_obj.get("6")
        if isinstance(filename, str) and filename:
            candidate = media_folder / filename
            if candidate.exists():
                return filename
            return f"missing:{filename}"
        if isinstance(alt_id, str) and alt_id:
            candidate = media_folder / alt_id
            if candidate.exists():
                return alt_id
            return f"missing:{alt_id}"
        return None

    def _format_timestamp(self, timestamp_ms: Any) -> str:
        if isinstance(timestamp_ms, (int, float)):
            dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
            return dt.strftime("%Y-%m-%dT%H:%M:%S")
        if isinstance(timestamp_ms, str):
            text = timestamp_ms.strip()
            if not text:
                return ""
            text = text.replace("Z", "+00:00")
            try:
                dt = datetime.fromisoformat(text)
            except ValueError as exc:
                raise ValueError(f"Invalid Wire timestamp format: {timestamp_ms}") from exc
            if dt.tzinfo is not None:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt.strftime("%Y-%m-%dT%H:%M:%S")
        return ""


# ----------------------
# Protobuf wire-format decoder (schema-less)
# ----------------------

def decode_protobuf_to_dict(data: bytes) -> Dict[str, Any]:
    msg, _ = _parse_message(data, 0, len(data))
    return msg


def _parse_message(data: bytes, start: int, end: int) -> Tuple[Dict[str, Any], int]:
    msg: Dict[str, Any] = {}
    i = start
    while i < end:
        tag, i = _read_varint(data, i)
        if tag is None:
            break
        field_num = tag >> 3
        wire_type = tag & 0x07
        if wire_type == 0:
            value, i = _read_varint(data, i)
        elif wire_type == 1:
            value = int.from_bytes(data[i:i + 8], "little", signed=False)
            i += 8
        elif wire_type == 2:
            length, i = _read_varint(data, i)
            if length is None:
                break
            raw = data[i:i + length]
            i += length
            value = _decode_length_delimited(raw)
        elif wire_type == 5:
            value = int.from_bytes(data[i:i + 4], "little", signed=False)
            i += 4
        else:
            # Unknown wire type; stop to avoid infinite loop
            break

        _add_field(msg, field_num, value)
    return msg, i


def _decode_length_delimited(raw: bytes) -> Any:
    if not raw:
        return ""
    # Try UTF-8 string
    try:
        text = raw.decode("utf-8")
        if text.isprintable() or all(ch in "\r\n\t" for ch in text):
            return text
    except UnicodeDecodeError:
        pass

    # Try embedded message
    nested, offset = _parse_message(raw, 0, len(raw))
    if nested and offset == len(raw):
        return nested

    # Fallback: base64 for binary data
    return "base64:" + base64.b64encode(raw).decode("ascii")


def _add_field(msg: Dict[str, Any], field_num: int, value: Any) -> None:
    key = str(field_num)
    if key in msg:
        existing = msg[key]
        if isinstance(existing, list):
            existing.append(value)
        else:
            msg[key] = [existing, value]
    else:
        msg[key] = value


def _read_varint(data: bytes, index: int) -> Tuple[Optional[int], int]:
    shift = 0
    result = 0
    i = index
    while i < len(data):
        b = data[i]
        i += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            return result, i
        shift += 7
        if shift >= 64:
            break
    return None, i
