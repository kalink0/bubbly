"""
Romeo Android Database Parser

Parses Romeo Android SQLite data and normalizes messages for Bubbly export.
"""

import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class RomeoAndroidDbParser:
    """Parser for Romeo Android SQLite databases."""

    PARSER_ARGS = {
        "account_name": "Optional. Owner display name used for outgoing messages.",
    }

    _DEFAULT_QUERY = """
        SELECT
            m.messageId AS message_id,
            m.chatPartnerId AS sender_id,
            cp.name AS sender_name,
            m.text AS content,
            m.date AS date_raw,
            m.transmissionStatus AS transmission_status,
            (
                SELECT ia.imageId
                FROM ImageAttachmentEntity ia
                WHERE ia.parentMessageId = m.messageId
                ORDER BY ia.id ASC
                LIMIT 1
            ) AS image_id,
            CASE WHEN EXISTS (
                SELECT 1
                FROM ImageAttachmentEntity ia
                WHERE ia.parentMessageId = m.messageId
            ) THEN 1 ELSE 0 END AS has_image
        FROM MessageEntity m
        LEFT JOIN ChatPartnerEntity cp
            ON cp.profileId = m.chatPartnerId
        ORDER BY m.date ASC, m.messageId ASC
    """

    _STATUS_SENT = "sent"
    _STATUS_RECEIVED = "received"
    _ACCOUNT_ID_PATTERN = re.compile(r"^planetromeo-room\.db\.(\d+)$")

    def parse(
        self,
        input_path: Path,
        media_folder: Path,
        account_name: str = "",
        **kwargs,
    ) -> Tuple[List[Dict], Dict]:
        """Parse Romeo DB into normalized messages and metadata."""
        del media_folder  # Romeo parser only uses DB metadata; files are not expected.
        db_path = self._resolve_db_path(Path(input_path))
        inferred_account_id = self._extract_account_id_from_db_name(db_path)
        owner_name = str(account_name or "").strip() or inferred_account_id or "Me"
        query = self._DEFAULT_QUERY

        messages: List[Dict] = []
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query).fetchall()

        for row in rows:
            msg = self._normalize_row(
                row,
                account_name=owner_name,
                default_chat=None,
            )
            if msg:
                messages.append(msg)

        metadata = {
            "user": kwargs.get("user"),
            "case": kwargs.get("case"),
            "chat_name": "Romeo Chats",
            "source": "Romeo",
            "platform": "android",
            "romeo_account_id": inferred_account_id,
        }
        return messages, metadata

    def _resolve_db_path(self, input_path: Path) -> Path:
        if input_path.is_file():
            if not self._looks_like_sqlite(input_path):
                raise ValueError(f"Expected a SQLite DB file, got: {input_path}")
            return input_path

        if input_path.is_dir():
            candidates = [
                path
                for path in sorted(input_path.iterdir())
                if path.is_file()
                if self._extract_account_id_from_db_name(path)
            ]
            if not candidates:
                raise FileNotFoundError(
                    "No Romeo DB candidate found in "
                    f"{input_path} (expected 'planetromeo-room.db.<digits>')"
                )
            if len(candidates) == 1:
                return candidates[0]
            raise ValueError(
                "Multiple Romeo SQLite files found; provide --input as the exact DB file path."
            )

        raise ValueError(f"Unsupported input path: {input_path}")

    def _looks_like_sqlite(self, file_path: Path) -> bool:
        try:
            with file_path.open("rb") as handle:
                header = handle.read(16)
        except OSError:
            return False
        return header == b"SQLite format 3\x00"

    def _normalize_row(
        self,
        row: sqlite3.Row,
        account_name: str,
        default_chat: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        message_id = self._first_value(row, "message_id", "messageId", "Message ID")
        sender_id = self._first_value(row, "sender_id", "chatPartnerId", "Contact ID")
        sender_name = self._first_value(row, "sender_name", "name", "Contact Name")
        content_raw = self._first_value(row, "content", "text", "Message Text") or ""
        date_raw = self._first_value(row, "date_raw", "date", "timestamp", "Timestamp")
        status_raw = self._first_value(
            row, "transmission_status", "transmissionStatus", "Status"
        )
        chat = self._first_value(row, "chat", "chat_name") or default_chat
        has_image = self._first_value(row, "has_image", "hasImage", "Image Contained?")
        explicit_is_owner = self._first_value(row, "is_owner", "isOwner", "outgoing")

        if date_raw is None:
            return None
        timestamp = self._normalize_timestamp(date_raw)
        if not timestamp:
            return None

        is_owner = self._is_owner(
            explicit_is_owner=explicit_is_owner,
            transmission_status=status_raw,
        )

        sender = account_name if is_owner else (sender_name or sender_id or "Unknown")
        if not chat:
            chat = sender_name or sender_id or "Unknown Chat"
        content = str(content_raw or "").strip()
        media = self._normalize_media_marker(
            row=row,
            message_id=str(message_id or ""),
            has_image=has_image,
            content=content,
        )
        if media and not content:
            content = "[Image]"

        normalized = {
            "timestamp": timestamp,
            "sender": sender,
            "content": content,
            "media": media,
            "url": self._extract_url(content),
            "is_owner": is_owner,
            "chat": chat,
        }
        if media and str(media).endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
            normalized["media_mime"] = "image/jpeg"
        return normalized

    def _extract_account_id_from_db_name(self, db_path: Path) -> str:
        match = self._ACCOUNT_ID_PATTERN.fullmatch(db_path.name)
        if match:
            return match.group(1)
        return ""

    def _is_owner(
        self,
        explicit_is_owner: Any,
        transmission_status: Any,
    ) -> bool:
        explicit_bool = self._to_optional_bool(explicit_is_owner)
        if explicit_bool is not None:
            return explicit_bool

        status = str(transmission_status or "").strip().lower()
        if status == self._STATUS_SENT:
            return True
        if status == self._STATUS_RECEIVED:
            return False
        return False

    def _normalize_media_marker(
        self,
        row: sqlite3.Row,
        message_id: str,
        has_image: Any,
        content: str,
    ) -> Optional[str]:
        media = self._first_value(row, "media", "image_file", "attachment", "image_id")
        if isinstance(media, str) and media.strip():
            value = media.strip()
            image_name = self._normalize_image_name(value)
            if not image_name.startswith("missing:"):
                return f"missing:{image_name}"
            return value

        if self._to_bool(has_image):
            mid = message_id or "unknown"
            return f"missing:romeo_image_{mid}.jpg"

        # Fallback: detect common inline image markers in exported text.
        text = content.lower()
        if re.search(r"\b(image|photo|picture)\b", text) and "http" not in text:
            mid = message_id or "unknown"
            return f"missing:romeo_image_{mid}.jpg"
        return None

    def _normalize_image_name(self, value: str) -> str:
        if "." in value.rsplit("/", 1)[-1]:
            return value
        return f"{value}.jpg"

    def _extract_url(self, content: str) -> Optional[str]:
        match = re.search(r"https?://\S+", content or "")
        return match.group(0) if match else None

    def _normalize_timestamp(self, value: Any) -> str:
        if value is None:
            raise ValueError("Missing timestamp value in Romeo message row")

        # Numeric epoch handling.
        if isinstance(value, (int, float)):
            return self._epoch_to_iso(float(value))

        text = str(value).strip()
        if not text:
            raise ValueError("Empty timestamp value in Romeo message row")
        if re.fullmatch(r"-?\d+(\.\d+)?", text):
            return self._epoch_to_iso(float(text))

        # ISO-like formats.
        candidate = text.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(candidate)
            if dt.tzinfo is not None:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt.strftime("%Y-%m-%dT%H:%M:%S")
        except ValueError:
            pass

        for fmt in (
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%d %H:%M:%S%z",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%d.%m.%Y %H:%M:%S",
            "%d.%m.%Y %H:%M",
        ):
            try:
                dt = datetime.strptime(text, fmt)
                if dt.tzinfo is not None:
                    dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
                return dt.strftime("%Y-%m-%dT%H:%M:%S")
            except ValueError:
                continue

        raise ValueError(f"Unsupported Romeo timestamp format: {value}")

    def _epoch_to_iso(self, epoch_value: float) -> str:
        # Heuristic: values above 1e11 are likely milliseconds.
        if abs(epoch_value) > 1e11:
            epoch_value = epoch_value / 1000.0
        dt = datetime.fromtimestamp(epoch_value, tz=timezone.utc).replace(tzinfo=None)
        return dt.strftime("%Y-%m-%dT%H:%M:%S")

    def _first_value(self, row: sqlite3.Row, *keys: str) -> Any:
        for key in keys:
            if key in row.keys():
                return row[key]
        return None

    def _to_optional_bool(self, value: Any) -> Optional[bool]:
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        text = str(value).strip().lower()
        if text in {"1", "true", "yes", "y", "t", "ja", "j"}:
            return True
        if text in {"0", "false", "no", "n", "f", "nein"}:
            return False
        return None

    def _to_bool(self, value: Any) -> bool:
        parsed = self._to_optional_bool(value)
        return bool(parsed) if parsed is not None else False
