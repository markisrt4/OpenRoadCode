// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT

#pragma once

#include <optional>
#include <string>

#include <zmq.hpp>

/** @brief Parsed command accepted by the native MapLibre renderer. */
struct MapCommand {
    std::string command;
    double latitude = 0.0;
    double longitude = 0.0;
    double zoom = 0.0;
    double bearing = 0.0;
    double pitch = 0.0;
    double south = 0.0;
    double west = 0.0;
    double north = 0.0;
    double east = 0.0;
    double padding = 40.0;
    std::string geojson;
};

/** @brief Non-blocking subscriber for map commands on the ORC message bus. */
class MapCommandServer {
public:
    explicit MapCommandServer(std::string endpoint = "tcp://127.0.0.1:5557");
    ~MapCommandServer() = default;

    MapCommandServer(const MapCommandServer&) = delete;
    MapCommandServer& operator=(const MapCommandServer&) = delete;

    std::optional<MapCommand> poll();

private:
    std::optional<MapCommand> parseCommand(const std::string& payload) const;

    std::string endpoint;
    zmq::context_t context{1};
    zmq::socket_t socket{context, zmq::socket_type::sub};
};
