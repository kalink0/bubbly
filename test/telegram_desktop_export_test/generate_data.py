"""Generate a large Telegram Desktop fixture dataset."""

from datetime import datetime, timedelta
from pathlib import Path
import json

OUTPUT_DIR = Path(__file__).resolve().parent / "testset_telegram_export"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
(OUTPUT_DIR / "media").mkdir(parents=True, exist_ok=True)

NUM_MESSAGES = 15000
start = datetime(2026, 2, 1, 12, 0, 0)

messages = []
for idx in range(NUM_MESSAGES):
    sender = "Owner TG" if idx % 2 == 0 else "Other TG"
    msg = {
        "id": idx + 1,
        "type": "message",
        "date": (start + timedelta(minutes=idx)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "from": sender,
        "text": f"Telegram message {idx + 1}",
    }
    if idx % 7 == 0:
        msg["file"] = "media/photo_1.jpg"
    messages.append(msg)

payload = {
    "name": "Telegram Test Chat",
    "messages": messages,
}

(OUTPUT_DIR / "result.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
print(f"Wrote {NUM_MESSAGES} messages to {OUTPUT_DIR / 'result.json'}")
