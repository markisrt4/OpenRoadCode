// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT

#pragma once

#include <optional>
#include <string>

#include <zmq.hpp>

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

/** Non-blocking ZeroMQ REP server for native map-renderer commands. */
class MapCommandServer {
public:
    explicit MapCommandServer(
        std::string endpoint = "ipc:///tmp/openroadcode-map-renderer"
    );
    ~MapCommandServer() = default;

    MapCommandServer(const MapCommandServer&) = delete;
    MapCommandServer& operator=(const MapCommandServer&) = delete;

    /** Receive and validate at most one pending command. */
    std::optional<MapCommand> poll();

private:
    std::optional<MapCommand> parseCommand(const std::string& payload) const;
    void sendReply(bool ok, const std::string& message);

    std::string endpoint;
    zmq::context_t context{1};
    zmq::socket_t socket{context, zmq::socket_type::rep};
};
