#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
HOST="${JEKYLL_HOST:-127.0.0.1}"
PORT="${JEKYLL_PORT:-4000}"
PYTHON_BIN="${PYTHON:-python3}"
GEMFILE="${SCRIPT_DIR}/docs-preview.Gemfile"
PREVIEW_ROOT="${XDG_CACHE_HOME:-${HOME}/.cache}/openroadcode/docs-preview"

if ! command -v bundle >/dev/null 2>&1; then
    cat >&2 <<'EOF'
Bundler is required for the OpenRoadCode documentation preview.

Install Ruby and Bundler using your platform package manager, then run:

    gem install bundler
EOF
    exit 1
fi

mkdir -p "${PREVIEW_ROOT}"

"${PYTHON_BIN}" "${SCRIPT_DIR}/docs_preview.py" \
    --source "${REPO_ROOT}" \
    --output "${PREVIEW_ROOT}/site"

export BUNDLE_GEMFILE="${GEMFILE}"
export BUNDLE_PATH="${PREVIEW_ROOT}/bundle"

if ! bundle check >/dev/null 2>&1; then
    echo "Installing Jekyll preview dependencies..."
    bundle install
fi

URL="http://${HOST}:${PORT}/docs/"

echo "OpenRoadCode documentation preview"
echo "Open: ${URL}"
echo "Press Ctrl-C to stop the Jekyll server."
echo

exec bundle exec jekyll serve \
    --source "${PREVIEW_ROOT}/site" \
    --destination "${PREVIEW_ROOT}/_site" \
    --host "${HOST}" \
    --port "${PORT}" \
    --livereload
