"""Parser-focused test cases using bundled fixture datasets."""

import unittest
import sys
import json
import shutil
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from parsers.generic_json_parser import GenericJsonParser
from parsers.romeo_android_db import RomeoAndroidDbParser
from parsers.telegram_desktop_chat_export import TelegramDesktopChatExportParser
from parsers.threema_messenger_backup import ThreemaMessengerBackupParser
from parsers.whatsapp_chat_export import WhatsAppChatExportParser
from parsers.wire_messenger_backup import WireMessengerBackupParser


class TestGenericJsonParser(unittest.TestCase):
    """Tests for generic JSON parser fixture handling."""

    def setUp(self):
        self.parser = GenericJsonParser()
        self.input_dir = REPO_ROOT / "test" / "testset_generic_json"
        self.media_dir = self.input_dir

    def test_resolve_json_paths_from_folder(self):
        """Parser should resolve both JSON fixtures from the generic test directory."""
        paths = self.parser.resolve_json_paths(self.input_dir)
        self.assertEqual(2, len(paths))
        names = sorted(p.name for p in paths)
        self.assertEqual(["example_group_chat.json", "example_second_chat.json"], names)

    def test_parse_group_chat_file(self):
        """Parser should normalize fixture messages and preserve key metadata fields."""
        json_path = self.input_dir / "example_group_chat.json"
        messages, metadata = self.parser.parse(
            json_path,
            self.media_dir,
            user="Tester",
            case="CASE-1",
        )
        self.assertEqual("Example Group Chat", metadata["chat_name"])
        self.assertEqual(3, len(messages))
        self.assertTrue(any(m.get("media") == "media/photo_001.png" for m in messages))
        self.assertTrue(any(m.get("is_owner") for m in messages))

    def test_parse_with_custom_messages_and_metadata_keys(self):
        """Parser should honor non-default messages/metadata key names."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            json_path = tmp_path / "custom.json"
            payload = {
                "custom_messages": [
                    {
                        "sender": "Alice",
                        "timestamp": "2026-02-01T12:00:00",
                        "content": "Hello",
                        "is_owner": True,
                    }
                ],
                "custom_meta": {"chat_name": "Custom Chat", "source": "Custom Source"},
            }
            json_path.write_text(json.dumps(payload), encoding="utf-8")
            messages, metadata = self.parser.parse(
                json_path,
                tmp_path,
                messages_key="custom_messages",
                metadata_key="custom_meta",
                user="Tester",
                case="CASE-CUSTOM",
            )
        self.assertEqual(1, len(messages))
        self.assertEqual("Custom Chat", metadata["chat_name"])
        self.assertEqual("Custom Source", metadata["source"])

    def test_invalid_timestamp_raises_value_error(self):
        """Invalid timestamp format in generic JSON should be rejected."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            json_path = tmp_path / "invalid_ts.json"
            payload = {
                "messages": [
                    {"sender": "Alice", "timestamp": "not-a-time", "content": "X"}
                ]
            }
            json_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValueError):
                self.parser.parse(json_path, tmp_path, user="Tester", case="CASE-TS")


class TestWhatsAppParser(unittest.TestCase):
    """Tests for WhatsApp export parser behavior against the sample text export."""

    def setUp(self):
        self.parser = WhatsAppChatExportParser()
        self.input_dir = REPO_ROOT / "test" / "whats_chat_export_test" / "testset_whatsapp_export"
        self.media_dir = self.input_dir

    def test_parse_ios_export(self):
        """Parser should parse iOS-style export lines and detect owner/media fields."""
        messages, metadata = self.parser.parse(
            self.input_dir,
            platform="ios",
            wa_account_name="M.",
            wa_account_number="+10000000000",
            user="Tester",
            case="CASE-2",
            chat_name="WhatsApp Test Chat",
        )
        self.assertEqual("WhatsApp", metadata["source"])
        self.assertEqual("WhatsApp Test Chat", metadata["chat_name"])
        self.assertGreater(len(messages), 10)
        self.assertTrue(any(m.get("is_owner") for m in messages))
        self.assertTrue(any(m.get("media") for m in messages))

    def test_parse_android_export(self):
        """Parser should parse Android format exports and detect media/url fields."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            txt_path = tmp_path / "chat.txt"
            txt_path.write_text(
                "\n".join([
                    "08/02/2026, 08:00 - Alice: Hello Android",
                    "08/02/2026, 08:01 - M.: image1.jpg",
                    "08/02/2026, 08:02 - Bob: Link https://example.com",
                ]),
                encoding="utf-8",
            )
            messages, metadata = self.parser.parse(
                tmp_path,
                platform="android",
                wa_account_name="M.",
                wa_account_number="+10000000000",
                user="Tester",
                case="CASE-AND",
                chat_name="Android Chat",
            )
        self.assertEqual("WhatsApp", metadata["source"])
        self.assertEqual(3, len(messages))
        self.assertTrue(any(m.get("media") == "image1.jpg" for m in messages))
        self.assertTrue(any(m.get("url") == "https://example.com" for m in messages))

    def test_invalid_platform_raises(self):
        """Unsupported WhatsApp platform should raise ValueError."""
        with self.assertRaises(ValueError):
            self.parser.parse(
                self.input_dir,
                platform="desktop",
                wa_account_name="M.",
                user="Tester",
                case="CASE-BAD",
                chat_name="Bad Platform",
            )


class TestTelegramParser(unittest.TestCase):
    """Tests for Telegram Desktop export parser fixture handling."""

    def setUp(self):
        self.parser = TelegramDesktopChatExportParser()
        self.input_dir = REPO_ROOT / "test" / "telegram_desktop_export_test" / "testset_telegram_export"
        self.media_dir = self.input_dir

    def test_parse_telegram_fixture(self):
        """Parser should parse Telegram fixture and preserve media references."""
        messages, metadata = self.parser.parse(
            self.input_dir,
            self.media_dir,
            tg_account_name="Owner TG",
            user="Tester",
            case="CASE-3",
        )
        self.assertEqual("Telegram", metadata["source"])
        self.assertEqual("Telegram Test Chat", metadata["chat_name"])
        self.assertGreaterEqual(len(messages), 10000)
        self.assertTrue(any(m.get("is_owner") for m in messages))
        self.assertTrue(any(m.get("media") == "media/photo_1.jpg" for m in messages))

    def test_invalid_telegram_timestamp_raises(self):
        """Invalid Telegram date values should raise ValueError."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            payload = {
                "name": "Broken Telegram",
                "messages": [
                    {"from": "A", "date": "invalid-date", "text": "Hello"}
                ],
            }
            (tmp_path / "result.json").write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValueError):
                self.parser.parse(tmp_path, tmp_path, tg_account_name="A", user="Tester", case="CASE-TG")


class TestThreemaParser(unittest.TestCase):
    """Tests for Threema CSV backup parser fixture handling."""

    def setUp(self):
        self.parser = ThreemaMessengerBackupParser()
        self.input_dir = REPO_ROOT / "test" / "threema_backup_test" / "testset_threema_backup"
        self.media_dir = self.input_dir

    def test_parse_threema_fixture(self):
        """Parser should parse large multi-chat Threema CSV fixture data."""
        messages, metadata = self.parser.parse(
            self.input_dir,
            self.media_dir,
            threema_account_name="Threema Owner",
            user="Tester",
            case="CASE-4",
        )
        self.assertEqual("Threema", metadata["source"])
        self.assertEqual("Threema Backup", metadata["chat_name"])
        self.assertGreaterEqual(len(messages), 10000)
        chats = {m.get("chat") for m in messages if m.get("chat")}
        self.assertGreaterEqual(len(chats), 2)
        self.assertTrue(any(m.get("is_owner") for m in messages))
        self.assertTrue(any(m.get("media") == "message_media_img1" for m in messages))

    def test_default_owner_name_is_me_when_not_provided(self):
        """Without threema_account_name, outbound messages should use 'Me' as sender."""
        messages, _ = self.parser.parse(
            self.input_dir,
            self.media_dir,
            user="Tester",
            case="CASE-4B",
        )
        owner_messages = [m for m in messages if m.get("is_owner")]
        self.assertTrue(owner_messages)
        self.assertTrue(all(m.get("sender") == "Me" for m in owner_messages[:20]))


class TestWireParser(unittest.TestCase):
    """Tests for Wire backup parser fixture handling."""

    def setUp(self):
        self.parser = WireMessengerBackupParser()
        self.input_dir = REPO_ROOT / "test" / "wire_backup_test" / "testset_wire_backup"
        self.media_dir = self.input_dir

    def test_parse_wire_fixture(self):
        """Parser should parse large multi-chat Wire binpb fixture data."""
        messages, metadata = self.parser.parse(
            self.input_dir,
            self.media_dir,
            user="Tester",
            case="CASE-5",
        )
        self.assertEqual("Wire Messenger", metadata["source"])
        self.assertEqual("Wire Backup", metadata["chat_name"])
        self.assertGreaterEqual(len(messages), 10000)
        chats = {m.get("chat") for m in messages if m.get("chat")}
        self.assertGreaterEqual(len(chats), 2)
        self.assertTrue(any(m.get("is_owner") for m in messages))
        self.assertTrue(any(m.get("media") == "wire_image.jpg" for m in messages))

    def test_missing_wire_media_marked_as_missing(self):
        """Missing media file should be marked with missing: prefix."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            copied = tmp_path / "wire"
            shutil.copytree(self.input_dir, copied)
            media_file = copied / "wire_image.jpg"
            if media_file.exists():
                media_file.unlink()
            messages, _ = self.parser.parse(copied, copied, user="Tester", case="CASE-5B")
        self.assertTrue(any(str(m.get("media") or "").startswith("missing:") for m in messages))


class TestRomeoAndroidDbParser(unittest.TestCase):
    """Tests for Romeo Android SQLite parser behavior."""

    def setUp(self):
        self.parser = RomeoAndroidDbParser()

    def test_parse_default_schema_and_image_marker(self):
        """Parser should read Romeo schema, normalize timestamp, and mark missing images."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            db_path = tmp_path / "romeo_114055512.db"
            self._create_romeo_db(db_path)

            messages, metadata = self.parser.parse(
                db_path,
                tmp_path,
                user="Tester",
                case="CASE-ROMEO",
            )

        self.assertEqual("Romeo", metadata["source"])
        self.assertEqual("android", metadata["platform"])
        self.assertEqual("114055512", metadata["romeo_account_id"])
        self.assertEqual("Romeo Chats", metadata["chat_name"])
        self.assertEqual(2, len(messages))
        self.assertEqual("2024-12-13T23:34:21", messages[0]["timestamp"])
        self.assertTrue(messages[0]["is_owner"])
        self.assertEqual("114055512", messages[0]["sender"])
        self.assertEqual("Matt", messages[0]["chat"])
        self.assertEqual("missing:img_001.jpg", messages[0].get("media"))
        self.assertEqual("Matt", messages[1]["sender"])
        self.assertFalse(messages[1]["is_owner"])
        self.assertEqual("Matt", messages[1]["chat"])

    def test_parse_second_message_as_non_owner(self):
        """Parser should keep incoming messages as non-owner with default detection."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            db_path = tmp_path / "romeo.sqlite"
            self._create_romeo_db(db_path)
            messages, _ = self.parser.parse(
                db_path,
                tmp_path,
                account_name="Owner",
                user="Tester",
                case="CASE-ROMEO-2",
            )

        self.assertEqual(2, len(messages))
        self.assertTrue(messages[0]["is_owner"])
        self.assertTrue(str(messages[0].get("media") or "").startswith("missing:"))
        self.assertFalse(messages[1]["is_owner"])

    def test_account_id_from_last_dot_segment(self):
        """Account id should be parsed from the segment after the last dot."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            db_path = tmp_path / "romeo.messages.413917007.sqlite"
            self._create_romeo_db(db_path)
            messages, metadata = self.parser.parse(
                db_path,
                tmp_path,
                user="Tester",
                case="CASE-ROMEO-4",
            )
        self.assertEqual("413917007", metadata["romeo_account_id"])
        self.assertTrue(messages)
        self.assertEqual("413917007", messages[0]["sender"])

    def test_extensionless_db_filename_with_account_id(self):
        """Parser should accept SQLite DB files without extension."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            db_path = tmp_path / "romeo.chat.413917007"
            self._create_romeo_db(db_path)
            messages, metadata = self.parser.parse(
                db_path,
                tmp_path,
                user="Tester",
                case="CASE-ROMEO-5",
            )
        self.assertEqual("413917007", metadata["romeo_account_id"])
        self.assertEqual(2, len(messages))

    def test_directory_with_extensionless_sqlite_file(self):
        """Parser should auto-discover extensionless SQLite files in a folder."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            db_path = tmp_path / "chat.backup.413917007"
            self._create_romeo_db(db_path)
            messages, metadata = self.parser.parse(
                tmp_path,
                tmp_path,
                user="Tester",
                case="CASE-ROMEO-6",
            )
        self.assertEqual("413917007", metadata["romeo_account_id"])
        self.assertEqual(2, len(messages))

    def _create_romeo_db(self, db_path: Path):
        import sqlite3

        with sqlite3.connect(str(db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE MessageEntity (
                    messageId TEXT NOT NULL PRIMARY KEY,
                    chatPartnerId TEXT NOT NULL,
                    text TEXT NOT NULL,
                    date TEXT NOT NULL,
                    transmissionStatus TEXT NOT NULL,
                    saved INTEGER NOT NULL,
                    unread INTEGER NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE ChatPartnerEntity (
                    profileId TEXT NOT NULL PRIMARY KEY,
                    onlineStatus TEXT,
                    name TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE ImageAttachmentEntity (
                    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                    parentMessageId TEXT NOT NULL,
                    imageId TEXT NOT NULL,
                    urlToken TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                INSERT INTO ChatPartnerEntity(profileId, onlineStatus, name)
                VALUES (?, ?, ?)
                """,
                ("92290179", "OFFLINE", "Matt"),
            )
            conn.execute(
                """
                INSERT INTO MessageEntity(messageId, chatPartnerId, text, date, transmissionStatus, saved, unread)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "O6977005.413917007",
                    "92290179",
                    "Hasta🤣",
                    "2024-12-13T23:34:21+0000",
                    "SENT",
                    0,
                    0,
                ),
            )
            conn.execute(
                """
                INSERT INTO MessageEntity(messageId, chatPartnerId, text, date, transmissionStatus, saved, unread)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "I6977005.413917008",
                    "92290179",
                    "Hello back",
                    "2024-12-13T23:35:21+0000",
                    "RECEIVED",
                    0,
                    1,
                ),
            )
            conn.execute(
                """
                INSERT INTO ImageAttachmentEntity(parentMessageId, imageId, urlToken)
                VALUES (?, ?, ?)
                """,
                ("O6977005.413917007", "img_001", "tok_001"),
            )
            conn.commit()


if __name__ == "__main__":
    unittest.main()
