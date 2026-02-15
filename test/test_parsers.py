import unittest
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from parsers.generic_json_parser import GenericJsonParser
from parsers.whatsapp_chat_export import WhatsAppChatExportParser


class TestGenericJsonParser(unittest.TestCase):
    def setUp(self):
        self.parser = GenericJsonParser()
        self.input_dir = REPO_ROOT / "test" / "testset_generic_json"
        self.media_dir = self.input_dir

    def test_resolve_json_paths_from_folder(self):
        paths = self.parser.resolve_json_paths(self.input_dir)
        self.assertEqual(2, len(paths))
        names = sorted(p.name for p in paths)
        self.assertEqual(["example_group_chat.json", "example_second_chat.json"], names)

    def test_parse_group_chat_file(self):
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
    def setUp(self):
        self.parser = WhatsAppChatExportParser()
        self.input_dir = REPO_ROOT / "test" / "whats_chat_export_test" / "testset_whatsapp_export"
        self.media_dir = self.input_dir

    def test_parse_ios_export(self):
        messages, metadata = self.parser.parse(
            self.input_dir,
            self.media_dir,
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


if __name__ == "__main__":
    unittest.main()
