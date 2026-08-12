#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

export DISPLAY=:2.0
export XDG_SESSION_TYPE=x11
export GDK_BACKEND=x11
export LIBGL_ALWAYS_SOFTWARE=1

exec sdrpp