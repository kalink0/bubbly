#!/usr/bin/env bash
set -euo pipefail

# Keep linting pragmatic for CI stability: fail on actual errors only.
PYTHONPATH=. pylint --errors-only $(find . -name "*.py" -not -path "./.venv/*" -not -path "./venv/*")
