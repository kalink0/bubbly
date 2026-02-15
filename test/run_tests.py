import unittest
from pathlib import Path


if __name__ == "__main__":
    test_dir = Path(__file__).resolve().parent
    suite = unittest.defaultTestLoader.discover(str(test_dir), pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
