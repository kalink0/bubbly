"""CLI summary output helpers."""


def _media_category(message):
    media = str(message.get("media") or "").strip()
    if media.startswith("missing:"):
        return "missing"

    mime = str(message.get("media_mime") or "").lower().strip()
    if mime.startswith("image/"):
        return "image"
    if mime.startswith("video/"):
        return "video"
    if mime.startswith("audio/"):
        return "audio"
    if mime in {
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }:
        return "document"

    ext = media.rsplit(".", 1)[-1].lower() if "." in media else ""
    if ext in {"jpg", "jpeg", "png", "gif", "webp"}:
        return "image"
    if ext in {"mp4", "mov", "webm", "3gp"}:
        return "video"
    if ext in {"mp3", "wav", "m4a", "aac", "opus", "ogg"}:
        return "audio"
    if ext in {"pdf", "doc", "docx", "xls", "xlsx"}:
        return "document"
    return "other"


def print_cli_summary(messages, metadata):
    """Print a concise summary of parsed messages and media categories."""
    total_messages = len(messages or [])
    default_chat = str((metadata or {}).get("chat_name") or "Chat").strip() or "Chat"
    chats = {
        str(msg.get("chat") or default_chat).strip() or default_chat
        for msg in (messages or [])
    }
    media_files = {}
    for msg in (messages or []):
        media = msg.get("media")
        if not media:
            continue
        media_text = str(media).strip()
        if not media_text:
            continue
        if media_text not in media_files:
            media_files[media_text] = _media_category(msg)

    found_media_files = {name for name in media_files if not name.startswith("missing:")}
    media_type_counts = {"audio": 0, "video": 0, "image": 0, "document": 0, "other": 0, "missing": 0}
    for category in media_files.values():
        media_type_counts[category] += 1

    print("Summary:")
    print(f" - Messages: {total_messages}")
    print(f" - Chats: {len(chats)}")
    print(f" - Found media files: {len(found_media_files)}")
    print(
        " - Media by type: "
        f"audio={media_type_counts['audio']}, "
        f"video={media_type_counts['video']}, "
        f"image={media_type_counts['image']}, "
        f"document={media_type_counts['document']}, "
        f"other={media_type_counts['other']}, "
        f"missing={media_type_counts['missing']}"
    )
