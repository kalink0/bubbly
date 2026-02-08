Bubbly – Bubble your chats

## Overview

`bubbly_launcher.py` parses chat exports and generates an HTML report with search, filters, time filtering, and media previews. It currently supports WhatsApp chat exports (iOS and Android).

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
  --extra_args platform=android wa_account_name="Owner Name" wa_account_number="+123" is_group_chat=false
```

Config file usage (optional `default_conf.json` next to the launcher, or `--config` to point to another file). CLI args override config values. `extra_args` merges config and CLI (CLI wins on conflicts).

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
  "extra_args": {
    "platform": "android",
    "wa_account_name": "Owner Name",
    "wa_account_number": "+123",
    "is_group_chat": false,
    "chat_name": "Chat Export"
  }
}
```

Notes:
- `--parser` must be one of: `whatsapp_export`.
- `extra_args` are parser-specific. For WhatsApp Chat Exports they include: `platform`, `wa_account_name`, `wa_account_number`, `is_group_chat`, `chat_name`.
