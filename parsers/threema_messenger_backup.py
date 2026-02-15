"""
Threema Messenger Backup Parser

Parses unencrypted Threema backups.
Supported inputs:
- CSV backup folders/zips (contacts.csv + message_*.csv / group_message_*.csv)
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import csv
import json
import mimetypes
import re


class ThreemaMessengerBackupParser:
    """
    Parser for Threema backups.
    """

    PARSER_ARGS = {
        "threema_account_name": "Optional. Display name used for outbound messages.",
    }

    def parse(
        self,
        input_folder: Path,
        media_folder: Path,
        threema_account_name: Optional[str] = None,
        **kwargs,
    ) -> Tuple[List[Dict], Dict]:
        input_folder = Path(input_folder)
        media_folder = Path(media_folder)

        if not self._has_csv_backup_structure(input_folder):
            raise FileNotFoundError(
                "Unsupported Threema input. Expected CSV backup structure with "
                "'contacts.csv' and at least one 'message_*.csv' file."
            )

        messages = self._parse_csv_backup(
            input_folder=input_folder,
            media_folder=media_folder,
            account_name=threema_account_name or "Me",
        )
        default_chat_name = "Threema Backup"

        unique_chats = sorted(
            {
                str(entry.get("chat") or "").strip()
                for entry in messages
                if str(entry.get("chat") or "").strip()
            }
        )
        if len(unique_chats) == 1:
            header_chat_name = unique_chats[0]
        else:
            header_chat_name = default_chat_name

        metadata = {
            "user": kwargs.get("user"),
            "case": kwargs.get("case"),
            "chat_name": header_chat_name,
            "source": "Threema",
            "platform": "mobile",
            "threema_account_name": threema_account_name,
        }

        return messages, metadata

    # ----------------------
    # CSV backup parser
    # ----------------------
    def _has_csv_backup_structure(self, root: Path) -> bool:
        return (root / "contacts.csv").is_file() and any(root.glob("message_*.csv"))

    def _parse_csv_backup(self, input_folder: Path, media_folder: Path, account_name: str) -> List[Dict]:
        contacts = self._load_contacts(input_folder / "contacts.csv")
        groups = self._load_groups(input_folder / "groups.csv")

        all_messages: List[Dict] = []
        for chat_file in sorted(input_folder.glob("message_*.csv")):
            contact_id = chat_file.stem.split("message_", 1)[1]
            contact = contacts.get(contact_id, {})
            chat_label = self._contact_display(contact, fallback=contact_id)
            all_messages.extend(
                self._parse_chat_csv(
                    chat_file=chat_file,
                    chat_name=chat_label,
                    peer_name=chat_label,
                    account_name=account_name,
                    media_folder=media_folder,
                    contact_index=contacts,
                    is_group=False,
                )
            )

        for group_file in sorted(input_folder.glob("group_message_*.csv")):
            group_id = group_file.stem.split("group_message_", 1)[1]
            group_name = groups.get(group_id, {}).get("groupname") or f"Group {group_id}"
            all_messages.extend(
                self._parse_chat_csv(
                    chat_file=group_file,
                    chat_name=group_name,
                    peer_name=None,
                    account_name=account_name,
                    media_folder=media_folder,
                    contact_index=contacts,
                    is_group=True,
                )
            )

        all_messages.sort(key=lambda msg: msg.get("timestamp") or "")
        return all_messages

    def _load_contacts(self, path: Path) -> Dict[str, Dict[str, str]]:
        mapping: Dict[str, Dict[str, str]] = {}
        if not path.is_file():
            return mapping

        for row in self._read_csv_rows(path):
            identity_id = (row.get("identity_id") or "").strip()
            identity = (row.get("identity") or "").strip()
            if identity_id:
                mapping[identity_id] = row
            if identity and identity not in mapping:
                mapping[identity] = row
        return mapping

    def _load_groups(self, path: Path) -> Dict[str, Dict[str, str]]:
        mapping: Dict[str, Dict[str, str]] = {}
        if not path.is_file():
            return mapping

        for row in self._read_csv_rows(path):
            group_uid = (row.get("group_uid") or "").strip()
            if group_uid:
                mapping[group_uid] = row
        return mapping

    def _parse_chat_csv(
        self,
        chat_file: Path,
        chat_name: str,
        peer_name: Optional[str],
        account_name: str,
        media_folder: Path,
        contact_index: Dict[str, Dict[str, str]],
        is_group: bool,
    ) -> List[Dict]:
        parsed: List[Dict] = []

        for row in self._read_csv_rows(chat_file):
            timestamp = self._timestamp_from_row(row)
            msg_type = (row.get("type") or "").strip().upper()
            uid = (row.get("uid") or "").strip()
            is_outbox = (row.get("isoutbox") or "0").strip() == "1"
            is_status = (row.get("isstatusmessage") or "0").strip() == "1"

            sender = self._resolve_sender(
                row=row,
                is_group=is_group,
                is_outbox=is_outbox,
                account_name=account_name,
                peer_name=peer_name,
                contact_index=contact_index,
                is_status=is_status,
            )

            content = self._build_content(row=row, msg_type=msg_type)
            media_info = self._resolve_media(
                uid=uid,
                msg_type=msg_type,
                media_folder=media_folder,
                body=row.get("body") or "",
            )
            media = media_info.get("media")
            if not content and media:
                content = f"[{msg_type.lower() if msg_type else 'media'}]"

            message = {
                "timestamp": timestamp,
                "sender": sender,
                "content": content,
                "media": media,
                "url": self._extract_url(content),
                "is_owner": is_outbox,
                "chat": chat_name,
            }
            if media_info.get("media_mime"):
                message["media_mime"] = media_info["media_mime"]
            if media_info.get("media_output"):
                message["media_output"] = media_info["media_output"]
            parsed.append(message)

        return parsed

    def _resolve_sender(
        self,
        row: Dict[str, str],
        is_group: bool,
        is_outbox: bool,
        account_name: str,
        peer_name: Optional[str],
        contact_index: Dict[str, Dict[str, str]],
        is_status: bool,
    ) -> str:
        if is_status:
            return "System"

        if is_outbox:
            return account_name

        if not is_group:
            return peer_name or "Unknown"

        identity = (row.get("identity") or "").strip()
        if identity and identity in contact_index:
            return self._contact_display(contact_index[identity], fallback=identity)
        if identity:
            return identity
        return "Unknown"

    def _build_content(self, row: Dict[str, str], msg_type: str) -> str:
        body = (row.get("body") or "").strip()
        caption = (row.get("caption") or "").strip()

        if msg_type == "TEXT":
            return body

        if caption:
            return caption

        if msg_type in {"IMAGE", "VIDEO", "FILE", "VOICEMESSAGE", "VOICE"}:
            return ""

        if msg_type:
            return f"[{msg_type.lower()}]"

        return body

    def _resolve_media(self, uid: str, msg_type: str, media_folder: Path, body: str) -> Dict[str, Optional[str]]:
        if not uid:
            return {"media": None, "media_mime": None, "media_output": None}

        if msg_type not in {"IMAGE", "VIDEO", "FILE", "VOICEMESSAGE", "VOICE"}:
            return {"media": None, "media_mime": None, "media_output": None}

        body_meta = self._parse_media_body_metadata(body)

        candidates: List[str] = [f"message_media_{uid}", f"message_thumbnail_{uid}"]
        if body_meta.get("filename"):
            candidates.append(str(body_meta["filename"]))
            candidates.append(str(Path(str(body_meta["filename"])).name))

        source_name: Optional[str] = None
        source_path: Optional[Path] = None
        for candidate in candidates:
            path = media_folder / candidate
            if path.exists():
                source_name = candidate
                source_path = path
                break

        if source_name is None or source_path is None:
            return {"media": f"message_media_{uid}", "media_mime": None, "media_output": None}

        media_mime = (
            self._detect_mime_from_magic(source_path)
            or body_meta.get("mime")
            or mimetypes.guess_type(source_name)[0]
        )
        media_output = source_name
        if not Path(source_name).suffix and media_mime:
            ext = self._extension_for_mime(media_mime)
            if ext:
                media_output = f"{source_name}.{ext}"

        return {"media": source_name, "media_mime": media_mime, "media_output": media_output}

    def _parse_media_body_metadata(self, body: str) -> Dict[str, Optional[str]]:
        result: Dict[str, Optional[str]] = {"filename": None, "mime": None}
        text = body.strip()
        if not text or not text.startswith("["):
            return result

        try:
            payload = json.loads(text)
        except Exception:
            return result

        if not isinstance(payload, list):
            return result

        if len(payload) > 2 and isinstance(payload[2], str) and "/" in payload[2]:
            result["mime"] = payload[2].strip().lower()
        for item in payload:
            if isinstance(item, str) and "." in item and not re.fullmatch(r"[0-9a-f]{32,64}", item):
                result["filename"] = item
                break
        return result

    def _detect_mime_from_magic(self, path: Path) -> Optional[str]:
        try:
            header = path.read_bytes()[:64]
        except Exception:
            return None
        if not header:
            return None

        if header.startswith(b"\xFF\xD8\xFF"):
            return "image/jpeg"
        if header.startswith(b"\x89PNG\r\n\x1A\n"):
            return "image/png"
        if header.startswith((b"GIF87a", b"GIF89a")):
            return "image/gif"
        if header.startswith(b"RIFF") and len(header) >= 12 and header[8:12] == b"WEBP":
            return "image/webp"
        if header.startswith(b"%PDF-"):
            return "application/pdf"
        if header.startswith(b"OggS"):
            return "audio/ogg"
        if header.startswith((b"ID3",)):
            return "audio/mpeg"
        if len(header) >= 2 and header[0] == 0xFF and (header[1] & 0xE0) == 0xE0:
            return "audio/mpeg"
        if header.startswith(b"RIFF") and len(header) >= 12 and header[8:12] == b"WAVE":
            return "audio/wav"
        if len(header) >= 12 and header[4:8] == b"ftyp":
            brand = header[8:12]
            if brand in {b"M4A ", b"isom", b"mp41", b"mp42"}:
                return "audio/mp4"
            if brand in {b"qt  "}:
                return "video/quicktime"
            return "video/mp4"
        if header.startswith(b"\x1A\x45\xDF\xA3"):
            return "video/webm"
        return None

    def _extension_for_mime(self, mime: str) -> Optional[str]:
        mime = (mime or "").lower().strip()
        mapping = {
            "image/jpeg": "jpg",
            "image/png": "png",
            "image/gif": "gif",
            "image/webp": "webp",
            "video/mp4": "mp4",
            "video/quicktime": "mov",
            "video/webm": "webm",
            "audio/mpeg": "mp3",
            "audio/mp4": "m4a",
            "audio/ogg": "ogg",
            "audio/wav": "wav",
            "application/pdf": "pdf",
        }
        if mime in mapping:
            return mapping[mime]
        guessed = mimetypes.guess_extension(mime) if mime else None
        if guessed:
            return guessed.lstrip(".")
        return None

    def _timestamp_from_row(self, row: Dict[str, str]) -> str:
        for key in ("posted_at", "created_at", "modified_at"):
            value = (row.get(key) or "").strip()
            if value:
                return self._to_iso_timestamp(value)
        return ""

    def _to_iso_timestamp(self, value: str) -> str:
        if not value:
            return ""

        try:
            if value.isdigit():
                dt = datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc)
                return dt.strftime("%Y-%m-%dT%H:%M:%S")
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if dt.tzinfo is not None:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt.strftime("%Y-%m-%dT%H:%M:%S")
        except Exception:
            return ""

    def _contact_display(self, contact: Dict[str, str], fallback: str) -> str:
        nick = (contact.get("nick_name") or "").strip()
        first = (contact.get("firstname") or "").strip()
        last = (contact.get("lastname") or "").strip()
        identity = (contact.get("identity") or "").strip()

        if nick:
            return nick
        full = f"{first} {last}".strip()
        if full:
            return full
        if identity:
            return identity
        return fallback

    def _read_csv_rows(self, path: Path) -> List[Dict[str, str]]:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            return [dict(row) for row in reader if row is not None]

    # ----------------------
    # Generic helpers
    # ----------------------
    def _extract_url(self, content: str) -> Optional[str]:
        match = re.search(r"https?://\S+", content or "")
        return match.group(0) if match else None

    def _as_bool(self, value: object) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes", "y"}:
                return True
            if normalized in {"false", "0", "no", "n"}:
                return False
        return bool(value)
