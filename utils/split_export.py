"""Helpers for split-by-chat HTML exports."""

import re
from datetime import datetime

from exporter import BubblyExporter

from .index_report import write_split_index


def safe_slug(value, fallback="chat"):
    """Convert an arbitrary value to a filesystem-safe slug."""
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value or "")).strip("._-")
    if not slug:
        return fallback
    return slug


def group_messages_by_chat(messages, default_chat_name):
    """Group parsed messages by chat label."""
    groups = {}
    for msg in messages:
        chat_name = str(msg.get("chat") or default_chat_name or "Chat").strip() or "Chat"
        groups.setdefault(chat_name, []).append(msg)
    return groups


def export_split_by_chat(messages, metadata, media_folder, output_folder, logo_path, safe_case):
    """Export one HTML report per chat and create a top-level index file."""
    chat_groups = group_messages_by_chat(messages, metadata.get("chat_name"))
    used_names = set()
    reports = []
    split_folder_name = "reports"
    split_output_folder = output_folder / split_folder_name
    split_output_folder.mkdir(parents=True, exist_ok=True)

    for chat_name, chat_messages in chat_groups.items():
        chat_slug = safe_slug(chat_name, "chat")
        base_name = f"{safe_case}_{chat_slug}"
        file_name = f"{base_name}.html"
        counter = 2
        while file_name in used_names:
            file_name = f"{base_name}_{counter}.html"
            counter += 1
        used_names.add(file_name)

        chat_meta = dict(metadata)
        chat_meta["chat_name"] = chat_name
        exporter = BubblyExporter(
            chat_messages,
            media_folder,
            split_output_folder,
            chat_meta,
            logo_path=logo_path,
        )
        exporter.export_html(output_html_name=file_name)
        media_count = len(
            {
                str(msg.get("media") or "").strip()
                for msg in chat_messages
                if str(msg.get("media") or "").strip()
                and not str(msg.get("media") or "").strip().startswith("missing:")
            }
        )
        reports.append(
            {
                "chat_name": chat_name,
                "file_name": file_name,
                "file_href": f"{split_folder_name}/{file_name}",
                "message_count": len(chat_messages),
                "media_count": media_count,
            }
        )

    if reports:
        write_split_index(
            output_folder,
            safe_case,
            reports,
            metadata.get("case"),
            creator=metadata.get("user"),
            logo_path=logo_path,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        print(f"Index saved to {output_folder / f'{safe_case}_index.html'}")
