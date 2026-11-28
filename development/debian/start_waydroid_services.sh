#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
set -euo pipefail
: "${DISPLAY:?Launch from the X11 desktop session}"
: "${XDG_RUNTIME_DIR:?No desktop user runtime directory}"
variables=(DISPLAY XDG_RUNTIME_DIR)
if [[ -n ${XAUTHORITY:-} ]]; then
    variables+=(XAUTHORITY)
else
    systemctl --user unset-environment XAUTHORITY
fi
systemctl --user import-environment "${variables[@]}"
exec systemctl --user start openroadcode-session.target
