"""Generate a large multi-chat Threema CSV backup fixture dataset."""

from datetime import datetime, timedelta
from pathlib import Path
import csv

OUTPUT_DIR = Path(__file__).resolve().parent / "testset_threema_backup"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

NUM_MESSAGES_PER_CHAT = 8000
start = datetime(2026, 2, 1, 10, 0, 0)

contacts_path = OUTPUT_DIR / "contacts.csv"
with contacts_path.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=["identity_id", "identity", "nick_name", "firstname", "lastname"],
    )
    writer.writeheader()
    writer.writerow(
        {
            "identity_id": "C1",
            "identity": "ABCD1234",
            "nick_name": "Test Contact",
            "firstname": "Test",
            "lastname": "Contact",
        }
    )
    writer.writerow(
        {
            "identity_id": "C2",
            "identity": "WXYZ5678",
            "nick_name": "Second Contact",
            "firstname": "Second",
            "lastname": "Contact",
        }
    )

def write_chat_csv(file_name: str, identity: str, prefix: str, media_uid: str) -> None:
    rows_path = OUTPUT_DIR / file_name
    with rows_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "uid",
                "posted_at",
                "type",
                "isoutbox",
                "isstatusmessage",
                "body",
                "caption",
                "identity",
            ],
        )
        writer.writeheader()

        for idx in range(NUM_MESSAGES_PER_CHAT):
            is_owner = 1 if idx % 2 == 0 else 0
            is_image = idx % 10 == 0
            writer.writerow(
                {
                    "uid": media_uid if is_image else f"{prefix}_msg{idx + 1}",
                    "posted_at": (start + timedelta(minutes=idx)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "type": "IMAGE" if is_image else "TEXT",
                    "isoutbox": str(is_owner),
                    "isstatusmessage": "0",
                    "body": "" if is_image else f"Threema {prefix} message {idx + 1}",
                    "caption": "",
                    "identity": identity,
                }
            )

    print(f"Wrote {NUM_MESSAGES_PER_CHAT} rows to {rows_path}")


write_chat_csv("message_C1.csv", "ABCD1234", "chat1", "img1")
write_chat_csv("message_C2.csv", "WXYZ5678", "chat2", "img2")

print(f"Total Threema messages: {NUM_MESSAGES_PER_CHAT * 2}")
