#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
HOST="${JEKYLL_HOST:-127.0.0.1}"
PORT="${JEKYLL_PORT:-4000}"
PYTHON_BIN="${PYTHON:-python3}"
GEMFILE="${SCRIPT_DIR}/docs-preview.Gemfile"
PREVIEW_ROOT="${XDG_CACHE_HOME:-${HOME}/.cache}/openroadcode/docs-preview"

is_termux() {
    [[ -n "${TERMUX_VERSION:-}" ]] ||
        [[ "${PREFIX:-}" == *"com.termux"* ]] ||
        [[ "${PREFIX:-}" == "/data/data/com.termux/files/usr" ]]
}

print_dependency_help() {
    cat >&2 <<'EOF'
The optional OpenRoadCode contributor documentation preview uses Jekyll and
therefore requires Ruby and Bundler. These are NOT OpenRoadCode runtime
dependencies and are not required to read the project documentation.

EOF

    if is_termux; then
        cat >&2 <<'EOF'
Termux example:

    pkg update
    pkg install ruby clang make pkg-config libffi libyaml
    gem install bundler

The compiler/build packages are included because some Ruby gems may build
native extensions on Android/Termux.

EOF
    else
        cat >&2 <<'EOF'
Debian/Ubuntu example:

    sudo apt install ruby-full build-essential
    gem install bundler

EOF
    fi

    cat >&2 <<'EOF'
Normal users can read the Markdown directly or use the published documentation.
EOF
}

if ! command -v ruby >/dev/null 2>&1 || ! command -v bundle >/dev/null 2>&1; then
    print_dependency_help
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

open_url() {
    local url="$1"

    if is_termux; then
        if command -v termux-open-url >/dev/null 2>&1; then
            termux-open-url "${url}" >/dev/null 2>&1
            return $?
        fi

        if [[ -x /system/bin/am ]]; then
            /system/bin/am start \
                -a android.intent.action.VIEW \
                -d "${url}" >/dev/null 2>&1
            return $?
        fi

        return 1
    fi

    if command -v xdg-open >/dev/null 2>&1; then
        xdg-open "${url}" >/dev/null 2>&1
    elif command -v open >/dev/null 2>&1; then
        open "${url}" >/dev/null 2>&1
    else
        return 1
    fi
}

open_browser_when_ready() {
    for _ in {1..60}; do
        if command -v curl >/dev/null 2>&1; then
            if curl --silent --fail --output /dev/null "${BROWSER_URL}"; then
                open_url "${BROWSER_URL}" || true
                return 0
            fi
        else
            sleep 1
            open_url "${BROWSER_URL}" || true
            return 0
        fi
        sleep 0.25
    done
}

open_browser_when_ready &

echo "OpenRoadCode contributor documentation preview"
if is_termux; then
    echo "Environment: Termux / Android"
fi
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
