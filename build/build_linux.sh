#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

python -m pip install -r "${SCRIPT_DIR}/requirements.txt"

VERSION="${GITHUB_REF_NAME:-v$(python -c 'from bubbly_version import BUBBLY_VERSION; print(BUBBLY_VERSION)')}"
BINARY_NAME="bubbly_${VERSION}"

pyinstaller \
  --noconfirm \
  --clean \
  --onefile \
  --name "${BINARY_NAME}" \
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
if [ -f "${SCRIPT_DIR}/README_release.txt" ]; then
  cp "${SCRIPT_DIR}/README_release.txt" "${SCRIPT_DIR}/dist/linux/README_release.txt"
  echo "Copied: ${SCRIPT_DIR}/dist/linux/README_release.txt"
fi

echo "Built: ${SCRIPT_DIR}/dist/linux/${BINARY_NAME}"
