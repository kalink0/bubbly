"""Launcher flow tests for exception logging behavior."""

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import bubbly_launcher


class _FailingParser:
    def parse(self, input_folder, media_folder=None, **kwargs):
        raise ValueError("Parser exploded")


class TestLauncherFlow(unittest.TestCase):
    """Tests for launcher-level exception/fallback log behavior."""

    def test_fallback_log_called_when_parse_args_fails(self):
        """Fallback logger should run for failures before RunLogger starts."""
        with patch("bubbly_launcher.parse_args", side_effect=RuntimeError("parse-args failed")):
            with patch("bubbly_launcher.write_fallback_exception_log") as fallback:
                fallback.return_value = Path("/tmp/fallback.log")
                with self.assertRaises(RuntimeError):
                    bubbly_launcher.main()
        self.assertEqual(1, fallback.call_count)

    def test_run_logger_file_created_when_parser_fails_in_context(self):
        """Failures inside run context should produce a run log entry."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_dir = tmp_path / "input"
            output_dir = tmp_path / "output"
            input_dir.mkdir(parents=True, exist_ok=True)
            output_dir.mkdir(parents=True, exist_ok=True)

            args = SimpleNamespace(
                parser="dummy",
                input=str(input_dir),
                output=str(output_dir),
                creator="Tester",
                case="CASE-FAIL",
                logo=None,
                parser_args=None,
                split_by_chat=False,
                log_level="info",
                _config={},
            )

            with patch("bubbly_launcher.parse_args", return_value=args):
                with patch.object(bubbly_launcher, "PARSERS", {"dummy": _FailingParser}):
                    with self.assertRaises(ValueError):
                        bubbly_launcher.main()

            bubbly_dirs = sorted(output_dir.glob("bubbly_*"))
            self.assertTrue(bubbly_dirs)
            log_files = list((bubbly_dirs[0] / "log").glob("bubbly_run_*.log"))
            self.assertTrue(log_files)
            log_text = log_files[0].read_text(encoding="utf-8")
            self.assertIn("Unhandled exception during run", log_text)


if __name__ == "__main__":
    unittest.main()
