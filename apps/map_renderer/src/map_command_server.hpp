#pragma once

#include <optional>
#include <string>


/**
 * @brief One command received by the native map renderer.
 *
 * The fields used depend on `command`: camera and position commands use
 * latitude/longitude fields, `fit_bounds` uses the bound and padding fields,
 * and `set_route` uses `geojson`.
 */
struct MapCommand {
    /** @brief Protocol command name. */
    std::string command;

    /** @brief Camera center latitude in decimal degrees. */
    double latitude = 0.0;
    /** @brief Camera center longitude in decimal degrees. */
    double longitude = 0.0;
    /** @brief MapLibre zoom level. */
    double zoom = 0.0;
    /** @brief Clockwise camera bearing in degrees. */
    double bearing = 0.0;
    /** @brief Camera pitch in degrees. */
    double pitch = 0.0;
    /** @brief South bound for `fit_bounds` command. */
    double south = 0.0;
    /** @brief West bound for `fit_bounds` command. */
    double west = 0.0;
    /** @brief North bound for `fit_bounds` command. */
    double north = 0.0;
    /** @brief East bound for `fit_bounds` command. */
    double east = 0.0;
    /** @brief Padding for `fit_bounds` command. */
    double padding = 40.0;

    /** @brief Serialized GeoJSON supplied by `set_route`. */
    std::string geojson;
};


/**
 * @brief Non-blocking Unix-domain socket server for map commands.
 *
 * Each client sends one JSON object and closes its connection. Call poll()
 * from the render loop to accept and parse at most one pending command.
 */
class MapCommandServer {
public:
    /**
     * @brief Create and bind the command socket.
     * @param socketPath Filesystem path for the Unix-domain socket.
     * @throws std::runtime_error if the socket cannot be created or bound.
     */
    explicit MapCommandServer(
        std::string socketPath =
            "/tmp/openroadcode-map-renderer.sock"
    );

    /** @brief Close the server and remove its socket file. */
    ~MapCommandServer();

    MapCommandServer(
        const MapCommandServer&
    ) = delete;

    MapCommandServer& operator=(
        const MapCommandServer&
    ) = delete;

    /**
     * @brief Read one pending command without waiting for a connection.
     * @return A validated command, or `std::nullopt` when no valid command is
     * available.
     */
    std::optional<MapCommand> poll();

private:
    std::optional<MapCommand> parseCommand(
        const std::string& payload
    ) const;

    std::string socketPath;
    int serverFd = -1;
};
