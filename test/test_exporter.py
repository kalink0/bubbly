"""Exporter integration tests for copied media and generated HTML content."""

import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from exporter import BubblyExporter
from utils.split_export import export_split_by_chat


class TestExporterMedia(unittest.TestCase):
    """Tests for media copy and reference behavior in HTML export output."""

    def _base_metadata(self):
        return {
            "user": "Tester",
            "case": "CASE-EXPORT",
            "chat_name": "Export Chat",
            "source": "Unit Test",
            "platform": "test",
        }

    def test_copies_media_files_to_output_media_folder(self):
        """Exporter should copy referenced media files into output/media."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            media_folder = tmp_path / "input_media"
            output_folder = tmp_path / "output"
            media_folder.mkdir(parents=True, exist_ok=True)

            (media_folder / "image1.jpg").write_bytes(b"\xFF\xD8\xFF\xE0testjpeg")
            (media_folder / "audio1.mp3").write_bytes(b"ID3testmp3")

            messages = [
                {
                    "sender": "Alice",
                    "content": "Photo",
                    "timestamp": "2026-02-01T12:00:00",
                    "media": "image1.jpg",
                    "is_owner": False,
                },
                {
                    "sender": "Bob",
                    "content": "Audio",
                    "timestamp": "2026-02-01T12:01:00",
                    "media": "audio1.mp3",
                    "is_owner": True,
                },
            ]

            exporter = BubblyExporter(messages, media_folder, output_folder, self._base_metadata())
            exporter.export_html("chat.html")

            self.assertTrue((output_folder / "media" / "image1.jpg").is_file())
            self.assertTrue((output_folder / "media" / "audio1.mp3").is_file())

    def test_generated_html_references_media_entries(self):
        """Generated HTML should embed both copied and missing media references."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            media_folder = tmp_path / "input_media"
            output_folder = tmp_path / "output"
            media_folder.mkdir(parents=True, exist_ok=True)

            (media_folder / "image1.jpg").write_bytes(b"\xFF\xD8\xFF\xE0testjpeg")

            messages = [
                {
                    "sender": "Alice",
                    "content": "Image message",
                    "timestamp": "2026-02-01T12:00:00",
                    "media": "image1.jpg",
                    "is_owner": False,
                },
                {
                    "sender": "Bob",
                    "content": "Missing file message",
                    "timestamp": "2026-02-01T12:01:00",
                    "media": "missing_file.jpg",
                    "is_owner": True,
                },
            ]

            exporter = BubblyExporter(messages, media_folder, output_folder, self._base_metadata())
            exporter.export_html("chat.html")

            html_content = (output_folder / "chat.html").read_text(encoding="utf-8")
            self.assertIn('"media": "image1.jpg"', html_content)
            self.assertIn('"media": "missing:missing_file.jpg"', html_content)
            self.assertFalse((output_folder / "media" / "missing_file.jpg").exists())


class TestExportModes(unittest.TestCase):
    """Tests for split and merged HTML export modes."""

    def _base_metadata(self):
        return {
            "user": "Tester",
            "case": "CASE-EXPORT",
            "chat_name": "Default Chat",
            "source": "Unit Test",
            "platform": "test",
        }

    def _sample_messages_two_chats(self):
        return [
            {
                "sender": "Alice",
                "content": "Chat one message",
                "timestamp": "2026-02-01T12:00:00",
                "media": None,
                "is_owner": False,
                "chat": "Chat One",
            },
            {
                "sender": "Bob",
                "content": "Chat two message",
                "timestamp": "2026-02-01T12:01:00",
                "media": None,
                "is_owner": True,
                "chat": "Chat Two",
            },
        ]

    def test_split_export_creates_one_html_per_chat_and_index(self):
        """Split export should create one report per chat plus a top-level index."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            media_folder = tmp_path / "media_in"
            output_folder = tmp_path / "output"
            media_folder.mkdir(parents=True, exist_ok=True)
            output_folder.mkdir(parents=True, exist_ok=True)

            export_split_by_chat(
                self._sample_messages_two_chats(),
                self._base_metadata(),
                media_folder,
                output_folder,
                logo_path=None,
                safe_case="CASE_EXPORT",
            )

            index_path = output_folder / "CASE_EXPORT_index.html"
            self.assertTrue(index_path.is_file())

            report_files = sorted((output_folder / "reports").glob("*.html"))
            self.assertEqual(2, len(report_files))

    def test_merged_export_creates_single_html_file(self):
        """Merged export should create one combined report file."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            media_folder = tmp_path / "media_in"
            output_folder = tmp_path / "output"
            media_folder.mkdir(parents=True, exist_ok=True)
            output_folder.mkdir(parents=True, exist_ok=True)

            exporter = BubblyExporter(
                self._sample_messages_two_chats(),
                media_folder,
                output_folder,
                self._base_metadata(),
            )
            exporter.export_html("CASE_EXPORT_report.html")

            self.assertTrue((output_folder / "CASE_EXPORT_report.html").is_file())
            self.assertFalse((output_folder / "reports").exists())


if __name__ == "__main__":
    unittest.main()
