"""Tests for processed-files collection helpers."""

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from utils.processed_files import collect_processed_files


class TestCollectProcessedFiles(unittest.TestCase):
    """Behavior tests for parser-specific processed file listing."""

    def test_romeo_folder_filters_to_name_pattern(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "planetromeo-room.db.114055512").write_text("x", encoding="utf-8")
            (root / "planetromeo-room.db.987654321").write_text("x", encoding="utf-8")
            (root / "planetromeo-room.db").write_text("x", encoding="utf-8")
            (root / "notes.txt").write_text("x", encoding="utf-8")

            files = collect_processed_files("romeo_android_db", root)

        self.assertEqual(
            [
                str(root / "planetromeo-room.db.114055512"),
                str(root / "planetromeo-room.db.987654321"),
            ],
            files,
        )

    def test_romeo_file_input_is_returned_directly(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db_file = root / "anyname.db"
            db_file.write_text("x", encoding="utf-8")

            files = collect_processed_files("romeo_android_db", db_file)

        self.assertEqual([str(db_file)], files)


if __name__ == "__main__":
    unittest.main()
