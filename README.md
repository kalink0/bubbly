Bubbly – Bubble your chats

## Overview

Bubbly generates an HTML report with search, filters, time filtering, and media previews in bubble view for chats from different messengers/exports. It currently supports:

- WhatsApp chat exports (iOS and Android)
- Telegram Desktop exports (JSON)
- Wire Messenger unencrypted backups (.wbu/.zip with .binpb files).
- Generic JSON chat exports (single JSON or multiple JSONs in a folder/zip).

![Example report](images/example.png)

## Usage

CLI usage (all required args on the CLI):

```bash
python messenger/bubbly/bubbly_launcher.py \
  --parser whatsapp_export \
  --input /path/to/chat_export.zip \
  --output /path/to/output \
  --creator "Analyst Name" \
  --case CASE-123 \
  --templates_folder messenger/bubbly/templates \
  --parser_args platform=android wa_account_name="Owner Name" wa_account_number="+123" is_group_chat=false
```

Config file usage (optional `default_conf.json` next to the launcher, or `--config` to point to another file). CLI args override config values. `parser_args` merges config and CLI (CLI wins on conflicts).

```bash
python messenger/bubbly/bubbly_launcher.py --config /path/to/config.json
```

Example config:

```json
{
  "parser": "whatsapp_export",
  "input": "/path/to/chat_export.zip",
  "output": "/path/to/output",
  "creator": "Analyst Name",
  "case": "CASE-123",
  "templates_folder": "messenger/bubbly/templates",
  "parser_args": {
    "platform": "android",
    "wa_account_name": "Owner Name",
    "wa_account_number": "+123",
    "is_group_chat": false,
    "chat_name": "Chat Export"
  }
}
```

Notes:
- `--parser` must be one of: `whatsapp_export`, `telegram_desktop_export`, `wire_messenger_backup`, `generic_json`.
- `parser_args` are parser-specific.
  - For WhatsApp Chat Exports: `platform`, `wa_account_name` (optional), `wa_account_number` (optional), `is_group_chat` (default: false), `chat_name` (optional).
  - For Telegram Desktop exports (JSON): `tg_account_name`, `chat_name`, `is_group_chat` (optional override).
  - For Wire Messenger backups: `chat_name` (optional override). Only unencrypted backups are supported.
  - For Generic JSON: `json_file` (optional), `messages_key` (optional), `metadata_key` (optional), `account_name` (optional), `is_group_chat` (optional override).

## Generic JSON schema

You can provide:
- A single `.json` file
- A folder or zip containing one or more `.json` files (each JSON is treated as a chat and merged into one report)

Required (per message):
- `sender`
- `timestamp` (ISO 8601, seconds required; timezone optional)
- `content` (or `text` / `message`)

Optional (per message):
- `media` (string path or object/list containing a path)
- `url`
- `is_owner`
- `chat` (or `chat_name`)

Optional (top-level):
- `chat_name`
- `metadata` (object; may include `is_group_chat`)
- `source`
- `platform`

Minimal example:

```json
{
  "chat_name": "Example Chat",
  "messages": [
    {
      "sender": "Alice",
      "timestamp": "2026-02-01T12:34:56Z",
      "content": "Hello"
    }
  ]
}
```
