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
  --paths "${REPO_ROOT}" \
  --hidden-import bubbly_version \
  --distpath "${SCRIPT_DIR}/dist/linux" \
  --workpath "${SCRIPT_DIR}/work/linux" \
  --specpath "${SCRIPT_DIR}/spec" \
  --add-data "${REPO_ROOT}/templates:templates" \
  "${REPO_ROOT}/bubbly_launcher.py"

if [ -f "${REPO_ROOT}/default_conf.json" ]; then
  cp "${REPO_ROOT}/default_conf.json" "${SCRIPT_DIR}/dist/linux/default_conf.json"
  echo "Copied: ${SCRIPT_DIR}/dist/linux/default_conf.json"
fi

echo "Built: ${SCRIPT_DIR}/dist/linux/bubbly"
