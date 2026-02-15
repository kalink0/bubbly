"""Generate a large multi-chat Wire .binpb fixture dataset."""

from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent / "testset_wire_backup"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

NUM_MESSAGES_TOTAL = 15000


def varint(n: int) -> bytes:
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            break
    return bytes(out)


def encode_field(field_num: int, value):
    if isinstance(value, int):
        return varint((field_num << 3) | 0) + varint(value)
    if isinstance(value, str):
        raw = value.encode("utf-8")
        return varint((field_num << 3) | 2) + varint(len(raw)) + raw
    if isinstance(value, dict):
        raw = encode_message(value)
        return varint((field_num << 3) | 2) + varint(len(raw)) + raw
    raise TypeError(f"Unsupported type: {type(value)!r}")


def encode_message(msg: dict) -> bytes:
    out = bytearray()
    for key, value in msg.items():
        field_num = int(key)
        if isinstance(value, list):
            for item in value:
                out.extend(encode_field(field_num, item))
        else:
            out.extend(encode_field(field_num, value))
    return bytes(out)


header = {"3": {"1": "owner-1"}}

conversations = {
    "1": header,
    "2": [
        {"1": {"1": "conv-1"}, "2": "Wire Test Chat A"},
        {"1": {"1": "conv-2"}, "2": "Wire Test Chat B"},
    ],
}

users = {
    "1": header,
    "4": [
        {"1": {"1": "owner-1"}, "2": "Owner Wire"},
        {"1": {"1": "user-2"}, "2": "Alice Wire"},
    ],
}

messages_list = []
base_ts = 1700000000000
for idx in range(NUM_MESSAGES_TOTAL):
    sender = "owner-1" if idx % 2 == 0 else "user-2"
    conversation = "conv-1" if idx % 2 == 0 else "conv-2"
    msg = {
        "2": base_ts + idx * 1000,
        "3": {"1": sender},
        "5": {"1": conversation},
    }
    if idx % 9 == 0:
        msg["7"] = {"3": "wire_image.jpg"}
    else:
        msg["6"] = {"1": f"Wire message {idx + 1}"}
    messages_list.append(msg)

messages = {
    "1": header,
    "3": messages_list,
}

(OUTPUT_DIR / "conversations_1.binpb").write_bytes(encode_message(conversations))
(OUTPUT_DIR / "users_1.binpb").write_bytes(encode_message(users))
(OUTPUT_DIR / "messages_1.binpb").write_bytes(encode_message(messages))

print(f"Wrote {NUM_MESSAGES_TOTAL} messages to {OUTPUT_DIR / 'messages_1.binpb'}")
