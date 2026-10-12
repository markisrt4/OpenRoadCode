// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT
#include "../src/map_command_server.hpp"
#include <cassert>
#include <chrono>
#include <iostream>
#include <stdexcept>
#include <thread>

int main() {
    const std::string endpoint = "ipc:///tmp/orc-vehicle-commands-" + std::to_string(
        std::chrono::steady_clock::now().time_since_epoch().count());
    zmq::context_t context;
    zmq::socket_t publisher(context, zmq::socket_type::pub);
    publisher.set(zmq::sockopt::linger, 0);
    publisher.bind(endpoint);
    MapCommandServer server(endpoint);
    const auto send = [&publisher](const std::string& payload) {
        publisher.send(zmq::buffer("map.command", 11), zmq::send_flags::sndmore);
        publisher.send(zmq::buffer(payload), zmq::send_flags::none);
    };
    const std::string sentinel = R"({"command":"set_center","latitude":0,"longitude":0})";
    // Wait for an actual subscription handshake instead of assuming a fixed startup delay.
    const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(2);
    bool ready = false;
    while (std::chrono::steady_clock::now() < deadline) {
        send(sentinel);
        std::this_thread::sleep_for(std::chrono::milliseconds(5));
        if (server.poll()) { ready = true; break; }
    }
    assert(ready);
    while (server.poll()) {}
    const auto receive = [&server]() {
        const auto end = std::chrono::steady_clock::now() + std::chrono::seconds(1);
        while (std::chrono::steady_clock::now() < end) {
            if (const auto command = server.poll()) return *command;
            std::this_thread::sleep_for(std::chrono::milliseconds(2));
        }
        throw std::runtime_error("command test timed out");
    };
    send(R"({"command":"set_position","latitude":42,"longitude":-83,
             "heading":80,"course":90,"speed_m_s":12,"smooth":true})");
    auto command = receive();
    assert(command.command == "set_position" && command.heading == 80 && command.course == 90);
    assert(command.speedMps == 12 && command.smoothPosition);
    send(R"({"command":"set_position","latitude":42,"longitude":-83})");
    command = receive();
    assert(!command.heading && !command.speedMps && !command.smoothPosition);
    send(R"({"command":"set_camera","latitude":42,"longitude":-83,"zoom":16,
             "bearing":90,"pitch":30,"follow_position":true})");
    assert(receive().followPosition);
    send(R"({"command":"set_follow","enabled":false})");
    command = receive();
    assert(command.command == "set_follow" && !command.enabled);
    for (const auto* invalid : {
        R"({"command":"set_position","latitude":42,"longitude":-83,"heading":"bad"})",
        R"({"command":"set_position","latitude":42,"longitude":-83,"speed_m_s":-1})",
        R"({"command":"set_position","latitude":42,"longitude":-83,"smooth":1})",
        R"({"command":"set_position","latitude":91,"longitude":-83})",
        R"({"command":"set_camera","latitude":42,"longitude":-83,"zoom":16,"bearing":90,"pitch":0,"follow_position":1})",
        R"({"command":"set_follow","enabled":"false"})"
    }) {
        send(invalid);
        send(sentinel);
        assert(receive().command == "set_center");
    }
    std::cout << "Vehicle command parsing checks passed\n";
}
