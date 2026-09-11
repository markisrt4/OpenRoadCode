#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
HOST="${JEKYLL_HOST:-127.0.0.1}"
PORT="${JEKYLL_PORT:-4000}"
PYTHON_BIN="${PYTHON:-python3}"
GEMFILE="${SCRIPT_DIR}/docs-preview.Gemfile"
PREVIEW_ROOT="${XDG_CACHE_HOME:-${HOME}/.cache}/openroadcode/docs-preview"

if ! command -v ruby >/dev/null 2>&1 || ! command -v bundle >/dev/null 2>&1; then
    cat >&2 <<'EOF'
The optional OpenRoadCode contributor documentation preview uses Jekyll and
therefore requires Ruby and Bundler. These are NOT OpenRoadCode runtime
dependencies and are not required to read the project documentation.

Debian/Ubuntu example:

    sudo apt install ruby-full build-essential
    gem install bundler

Normal users can read the Markdown directly or use the published documentation.
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
    echo "Installing optional Jekyll preview dependencies..."
    bundle install
fi

URL="http://${HOST}:${PORT}/docs/"
BROWSER_URL="${URL}"
if [[ "${HOST}" == "0.0.0.0" ]]; then
    BROWSER_URL="http://127.0.0.1:${PORT}/docs/"
fi

open_browser_when_ready() {
    local opener=""
    if command -v xdg-open >/dev/null 2>&1; then
        opener="xdg-open"
    elif command -v termux-open-url >/dev/null 2>&1; then
        opener="termux-open-url"
    elif command -v open >/dev/null 2>&1; then
        opener="open"
    else
        return 0
    fi

    for _ in {1..60}; do
        if command -v curl >/dev/null 2>&1; then
            if curl --silent --fail --output /dev/null "${BROWSER_URL}"; then
                "${opener}" "${BROWSER_URL}" >/dev/null 2>&1 || true
                return 0
            fi
        else
            sleep 1
            "${opener}" "${BROWSER_URL}" >/dev/null 2>&1 || true
            return 0
        fi
        sleep 0.25
    done
}

open_browser_when_ready &

echo "OpenRoadCode contributor documentation preview"
echo "Open: ${BROWSER_URL}"
echo "The browser will open automatically when the Jekyll server is ready."
echo "Press Ctrl-C to stop the preview server."
echo

exec bundle exec jekyll serve \
    --source "${PREVIEW_ROOT}/site" \
    --destination "${PREVIEW_ROOT}/_site" \
    --host "${HOST}" \
    --port "${PORT}" \
    --livereload
