// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT

#include "../src/map_command_server.hpp"

#include <chrono>
#include <iostream>
#include <thread>

int main(int argc, char** argv)
{
    const std::string endpoint = argc > 1
        ? argv[1]
        : "tcp://127.0.0.1:15562";

    MapCommandServer server(endpoint);
    std::cout << "Waiting for map commands. Press Ctrl-C to stop.\n";

    while (true) {
        if (const auto command = server.poll()) {
            std::cout << "received: " << command->command << '\n';
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(5));
    }
}
