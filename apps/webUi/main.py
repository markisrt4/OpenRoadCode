# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""OpenRoadCode browser application bootstrap."""

import os

from apps.webUi.menu_catalog import create_web_ui_menu_pages
from frontends.web import create_web_frontend

app = create_web_frontend(create_web_ui_menu_pages())

if __name__ == "__main__":
    host = os.environ.get("OPENROADCODE_WEB_HOST", "0.0.0.0")
    port = int(os.environ.get("OPENROADCODE_WEB_PORT", "5000"))
    debug = os.environ.get("OPENROADCODE_WEB_DEBUG", "0") == "1"
    app.run(host=host, port=port, debug=debug)
