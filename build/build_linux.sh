#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

python -m pip install -r "${SCRIPT_DIR}/requirements.txt"

pyinstaller \
  --noconfirm \
  --clean \
  --onefile \
  --name bubbly \
  --distpath "${SCRIPT_DIR}/dist/linux" \
  --workpath "${SCRIPT_DIR}/work/linux" \
  --specpath "${SCRIPT_DIR}/spec" \
  --add-data "${REPO_ROOT}/templates:templates" \
  --add-data "${REPO_ROOT}/default_conf.json:." \
  "${REPO_ROOT}/bubbly_launcher.py"

echo "Built: ${SCRIPT_DIR}/dist/linux/bubbly"
