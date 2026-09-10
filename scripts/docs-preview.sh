#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
SITE_ROOT="${ORC_SITE_ROOT:-${REPO_ROOT}/../openroadcode-site}"
HOST="${JEKYLL_HOST:-127.0.0.1}"
PORT="${JEKYLL_PORT:-4000}"

if [[ ! -d "${SITE_ROOT}" ]]; then
    cat >&2 <<EOF
OpenRoadCode website checkout not found:

    ${SITE_ROOT}

Clone markisrt4/openroadcode-site beside this repository, or set ORC_SITE_ROOT
to an existing checkout.
EOF
    exit 1
fi

SITE_SERVE="${SITE_ROOT}/scripts/serve.sh"
if [[ ! -f "${SITE_SERVE}" ]]; then
    echo "Website serve helper not found: ${SITE_SERVE}" >&2
    exit 1
fi

echo "Source: ${REPO_ROOT}"
echo "Site:   ${SITE_ROOT}"
echo "Open:   http://${HOST}:${PORT}/docs/"
echo "Press Ctrl-C to stop the Jekyll server."
echo

exec bash "${SITE_SERVE}" \
    --source "${REPO_ROOT}" \
    --host "${HOST}" \
    --port "${PORT}"
