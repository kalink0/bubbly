#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

python -m pip install -r "${SCRIPT_DIR}/requirements.txt"

if [ "${GITHUB_REF_TYPE:-}" = "tag" ] && [ -n "${GITHUB_REF_NAME:-}" ]; then
  VERSION="${GITHUB_REF_NAME}"
else
  VERSION="v$(python -c 'from bubbly_version import BUBBLY_VERSION; print(BUBBLY_VERSION)')"
fi
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

echo "Built: ${SCRIPT_DIR}/dist/linux/${BINARY_NAME}"
