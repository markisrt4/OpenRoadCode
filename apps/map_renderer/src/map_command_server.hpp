#pragma once

#include <optional>
#include <string>


struct SetCenterCommand {
    double latitude;
    double longitude;
};


class MapCommandServer {
public:
    explicit MapCommandServer(
        std::string socketPath =
            "/tmp/openroadcode-map-renderer.sock"
    );

    ~MapCommandServer();

    MapCommandServer(
        const MapCommandServer&
    ) = delete;

    MapCommandServer& operator=(
        const MapCommandServer&
    ) = delete;

    std::optional<SetCenterCommand>
    poll();

private:
    std::optional<SetCenterCommand>
    parseCommand(
        const std::string& payload
    ) const;

    std::string socketPath;
    int serverFd = -1;
};
