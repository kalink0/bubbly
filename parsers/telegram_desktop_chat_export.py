"""
Telegram Desktop Chat Export Parser

Created: 2026-02-08
Author: Kalink0
Description: Creates Bubbly JSON from Telegram Desktop exports.
"""

from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any
import json
import re


class TelegramDesktopChatExportParser:
    """
    Parser for Telegram Desktop chat exports (machine-readable JSON).
    """
    EXTRA_ARGS = {
        "tg_account_name": "Optional. Account display name for is_owner detection.",
        "is_group_chat": "Optional. true or false to override auto-detect.",
    }

    def parse(
        self,
        input_folder: Path,
        media_folder: Path,
        tg_account_name: Optional[str] = None,
        **kwargs
    ) -> Tuple[List[Dict], Dict]:
        input_folder = Path(input_folder)

        json_path = self._find_result_json(input_folder)
        with json_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)

        raw_messages = data.get("messages", [])
        if not isinstance(raw_messages, list):
            raise ValueError("Invalid Telegram export: 'messages' is not a list")

        messages: List[Dict] = []
        chat_name = data.get("name")
        for msg in raw_messages:
            if not isinstance(msg, dict):
                continue

            sender = msg.get("from") or msg.get("actor") or "System"
            content = self._render_text(msg.get("text"))
            if not content:
                content = self._fallback_content(msg)

            timestamp = msg.get("date") or ""
            media = self._extract_media(msg)
            url = self._extract_url(content)

            messages.append({
                "timestamp": timestamp,
                "sender": sender,
                "content": content,
                "media": media,
                "url": url,
                "is_owner": bool(tg_account_name and sender == tg_account_name),
                "chat": chat_name,
            })

        metadata = {
            "user": kwargs.get("user"),
            "case": kwargs.get("case"),
            "chat_name": chat_name,
            "source": "Telegram",
            "tg_account_name": tg_account_name,
            "is_group_chat": self._infer_group_chat(data, kwargs),
            "platform": "desktop",
        }

        return messages, metadata

    def _find_result_json(self, input_folder: Path) -> Path:
        preferred = input_folder / "result.json"
        if preferred.is_file():
            return preferred

        json_files = list(input_folder.glob("*.json"))
        if len(json_files) == 1:
            return json_files[0]
        if json_files:
            raise FileNotFoundError(
                "Multiple .json files found; expected result.json"
            )
        raise FileNotFoundError(f"No .json export found in {input_folder}")

    def _render_text(self, text: Any) -> str:
        if isinstance(text, str):
            return text.strip()
        if isinstance(text, list):
            parts: List[str] = []
            for item in text:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    value = item.get("text")
                    if value:
                        parts.append(str(value))
            return "".join(parts).strip()
        return ""

    def _fallback_content(self, msg: Dict[str, Any]) -> str:
        media_type = msg.get("media_type")
        if media_type:
            return f"[{media_type}]"
        action = msg.get("action")
        if action:
            return f"[{action}]"
        return ""

    def _extract_media(self, msg: Dict[str, Any]) -> Optional[str]:
        file_path = msg.get("file")
        if not file_path or not isinstance(file_path, str):
            return None
        if "File not included" in file_path:
            return None
        return file_path

    def _extract_url(self, content: str) -> Optional[str]:
        url_pattern = re.compile(r"https?://\\S+")
        match = url_pattern.search(content or "")
        return match.group(0) if match else None

    def _infer_group_chat(self, data: Dict[str, Any], kwargs: Dict[str, Any]) -> bool:
        if "is_group_chat" in kwargs:
            return bool(kwargs.get("is_group_chat"))
        chat_type = data.get("type")
        if not chat_type:
            return False
        return chat_type not in {"personal_chat", "private_chat", "saved_messages"}
