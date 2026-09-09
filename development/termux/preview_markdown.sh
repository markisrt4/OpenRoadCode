#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"

MARKDOWN_PATH="${1:-docs/README.md}"
HOST="${GRIP_HOST:-127.0.0.1}"
PORT="${GRIP_PORT:-6419}"

if [[ "${MARKDOWN_PATH}" != /* ]]; then
    MARKDOWN_PATH="${REPO_ROOT}/${MARKDOWN_PATH}"
fi

if [[ ! -f "${MARKDOWN_PATH}" ]]; then
    echo "Markdown file not found: ${MARKDOWN_PATH}" >&2
    exit 1
fi

if ! command -v grip >/dev/null 2>&1; then
    cat >&2 <<'EOF'
The 'grip' Markdown preview server is not installed.

Install it in the active Python environment with:

    python -m pip install grip

Then rerun this script.
EOF
    exit 1
fi

URL="http://${HOST}:${PORT}"

echo "Previewing: ${MARKDOWN_PATH}"
echo "Open:       ${URL}"
echo "Press Ctrl-C to stop the preview server."
echo

exec grip "${MARKDOWN_PATH}" "${HOST}:${PORT}"
