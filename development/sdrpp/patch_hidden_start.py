#!/usr/bin/env python3
"""Patch SDR++'s GLFW backend to support ORC-controlled hidden startup."""

from pathlib import Path
import sys

source_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "SDRPlusPlus"
backend = source_root / "core" / "backends" / "glfw" / "backend.cpp"
text = backend.read_text(encoding="utf-8")

include_marker = "#include <filesystem>\n"
if "#include <cstdlib>" not in text:
    if include_marker not in text:
        raise SystemExit("Could not locate SDR++ backend include marker")
    text = text.replace(include_marker, include_marker + "#include <cstdlib>\n", 1)

hint = '''            // OpenRoadCode can create the GLFW client unmapped so X11 can\n            // reparent it before the desktop window manager ever paints it.\n            if (std::getenv("ORC_SDRPP_START_HIDDEN") != nullptr) {\n                glfwWindowHint(GLFW_VISIBLE, GLFW_FALSE);\n            }\n\n'''
create_marker = "            // Create window with graphics context\n            monitor = glfwGetPrimaryMonitor();\n"
if "ORC_SDRPP_START_HIDDEN" not in text:
    if create_marker not in text:
        raise SystemExit("Could not locate SDR++ GLFW window creation marker")
    text = text.replace(create_marker, hint + create_marker, 1)

backend.write_text(text, encoding="utf-8")
print(f"[+] Patched hidden SDR++ startup support: {backend}")
