// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT
#include "orc_logging.hpp"
#include <initializer_list>

int main() {
    for (const char* severity : {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}) {
        orc::log(severity, "map_renderer.routes", "route.test",
                 "Route \"accepted\"\nnext line: café", "route-17", "set_route");
    }
    orc::log("INFO", "map_renderer.commands", "command.test", "Map command received");
    return 0;
}
