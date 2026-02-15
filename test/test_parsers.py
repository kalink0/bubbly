"""Parser-focused test cases using bundled fixture datasets."""

import unittest
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from parsers.generic_json_parser import GenericJsonParser
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


if __name__ == "__main__":
    unittest.main()
