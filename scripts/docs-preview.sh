#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

MARKDOWN_PATH="${1:-docs/README.md}"
HOST="${GRIP_HOST:-127.0.0.1}"
PORT="${GRIP_PORT:-6419}"
PYTHON_BIN="${PYTHON:-python}"

if [[ "${MARKDOWN_PATH}" != /* ]]; then
    MARKDOWN_PATH="${REPO_ROOT}/${MARKDOWN_PATH}"
fi

if [[ ! -f "${MARKDOWN_PATH}" ]]; then
    echo "Markdown file not found: ${MARKDOWN_PATH}" >&2
    exit 1
fi

exec "${PYTHON_BIN}" "${SCRIPT_DIR}/docs_preview.py" \
    --source "${REPO_ROOT}" \
    --document "${MARKDOWN_PATH}" \
    --host "${HOST}" \
    --port "${PORT}"
