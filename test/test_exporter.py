import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from exporter import BubblyExporter


class TestExporterMedia(unittest.TestCase):
    def _base_metadata(self):
        return {
            "user": "Tester",
            "case": "CASE-EXPORT",
            "chat_name": "Export Chat",
            "source": "Unit Test",
            "platform": "test",
        }

    def test_copies_media_files_to_output_media_folder(self):
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


if __name__ == "__main__":
    unittest.main()
