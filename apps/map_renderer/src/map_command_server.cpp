// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT

#include "map_command_server.hpp"

#include <rapidjson/document.h>
#include <rapidjson/stringbuffer.h>
#include <rapidjson/writer.h>

#include <sys/socket.h>
#include <sys/un.h>

#include <cerrno>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <unistd.h>


MapCommandServer::MapCommandServer(
    std::string socketPath_
)
    : socketPath(std::move(socketPath_))
{
    /*
     * Remove any stale socket left behind by
     * an unclean shutdown.
     */
    ::unlink(
        socketPath.c_str()
    );

    serverFd = ::socket(
        AF_UNIX,
        SOCK_STREAM | SOCK_NONBLOCK,
        0
    );

    if (serverFd < 0) {
        throw std::runtime_error(
            "Failed to create map command socket"
        );
    }

    sockaddr_un address{};
    address.sun_family = AF_UNIX;

    if (
        socketPath.size() >=
        sizeof(address.sun_path)
    ) {
        ::close(serverFd);

        throw std::runtime_error(
            "Map command socket path is too long"
        );
    }

    std::strncpy(
        address.sun_path,
        socketPath.c_str(),
        sizeof(address.sun_path) - 1
    );

    if (
        ::bind(
            serverFd,
            reinterpret_cast<
                sockaddr*
            >(&address),
            sizeof(address)
        ) < 0
    ) {
        const std::string error =
            std::strerror(errno);

        ::close(serverFd);
        serverFd = -1;

        throw std::runtime_error(
            "Failed to bind map command socket: " +
            error
        );
    }

    if (
        ::listen(
            serverFd,
            4
        ) < 0
    ) {
        const std::string error =
            std::strerror(errno);

        ::close(serverFd);
        serverFd = -1;

        throw std::runtime_error(
            "Failed to listen on map command socket: " +
            error
        );
    }

    std::cout
        << "Map command socket: "
        << socketPath
        << '\n';
}


MapCommandServer::~MapCommandServer()
{
    if (serverFd >= 0) {
        ::close(serverFd);
    }

    ::unlink(
        socketPath.c_str()
    );
}


std::optional<MapCommand>
MapCommandServer::poll()
{
    sockaddr_un clientAddress{};
    socklen_t clientAddressLength =
        sizeof(clientAddress);

    const int clientFd =
        ::accept4(
            serverFd,
            reinterpret_cast<
                sockaddr*
            >(&clientAddress),
            &clientAddressLength,
            0
        );

    if (clientFd < 0) {
        if (
            errno == EAGAIN ||
            errno == EWOULDBLOCK
        ) {
            return std::nullopt;
        }

        std::cerr
            << "Map command accept failed: "
            << std::strerror(errno)
            << '\n';

        return std::nullopt;
    }

    std::string payload;

    char buffer[4096];

    while (true) {
        const ssize_t count =
            ::read(
                clientFd,
                buffer,
                sizeof(buffer)
            );

        if (count > 0) {
            payload.append(
                buffer,
                static_cast<std::size_t>(count)
            );

            continue;
        }

        if (count == 0) {
            break;
        }

        if (errno == EINTR) {
            continue;
        }

        std::cerr
            << "Map command read failed: "
            << std::strerror(errno)
            << '\n';

        ::close(clientFd);

        return std::nullopt;
    }

    ::close(clientFd);

    if (payload.empty()) {
        return std::nullopt;
    }

    return parseCommand(
        payload
    );
}


std::optional<MapCommand>
MapCommandServer::parseCommand(
    const std::string& payload
) const
{
    rapidjson::Document document;

    document.Parse(
        payload.c_str()
    );

    if (document.HasParseError()) {
        std::cerr
            << "Invalid map command JSON\n";

        return std::nullopt;
    }

    if (
        !document.IsObject() ||
        !document.HasMember("command") ||
        !document["command"].IsString()
    ) {
        return std::nullopt;
    }

    MapCommand command;

    command.command =
        document["command"].GetString();

    if (
        command.command == "set_route"
    ) {
        if (
            !document.HasMember("geojson") ||
            !document["geojson"].IsObject()
        ) {
            return std::nullopt;
        }

        rapidjson::StringBuffer buffer;

        rapidjson::Writer<
            rapidjson::StringBuffer
        > writer(buffer);

        document["geojson"].Accept(writer);

        command.geojson =
            buffer.GetString();

        return command;
    }

    if (
        command.command == "set_center"
    ) {
        if (
            !document.HasMember("latitude") ||
            !document["latitude"].IsNumber() ||
            !document.HasMember("longitude") ||
            !document["longitude"].IsNumber()
        ) {
            return std::nullopt;
        }

        command.latitude =
            document["latitude"].GetDouble();

        command.longitude =
            document["longitude"].GetDouble();

        return command;
    }

    if (
        command.command == "set_camera"
    ) {
        if (
            !document.HasMember("latitude") ||
            !document["latitude"].IsNumber() ||
            !document.HasMember("longitude") ||
            !document["longitude"].IsNumber() ||
            !document.HasMember("zoom") ||
            !document["zoom"].IsNumber() ||
            !document.HasMember("bearing") ||
            !document["bearing"].IsNumber() ||
            !document.HasMember("pitch") ||
            !document["pitch"].IsNumber()
        ) {
            return std::nullopt;
        }

        command.latitude =
            document["latitude"].GetDouble();

        command.longitude =
            document["longitude"].GetDouble();

        command.zoom =
            document["zoom"].GetDouble();

        command.bearing =
            document["bearing"].GetDouble();

        command.pitch =
            document["pitch"].GetDouble();

        return command;
    }

    if (command.command == "fit_bounds") {
        if (
            !document.HasMember("south") ||
            !document["south"].IsNumber() ||
            !document.HasMember("west") ||
            !document["west"].IsNumber() ||
            !document.HasMember("north") ||
            !document["north"].IsNumber() ||
            !document.HasMember("east") ||
            !document["east"].IsNumber()
        ) {
            std::cerr
                << "fit_bounds missing required bounds\n";
            return std::nullopt;
        }

        command.south = document["south"].GetDouble();
        command.north = document["north"].GetDouble();
        command.west  = document["west"].GetDouble();
        command.east =  document["east"].GetDouble();

        if (document.HasMember("padding") && document["padding"].IsNumber())
        {
            command.padding = document["padding"].GetDouble();
        }

        return command;
    }

    if (command.command == "set_position") {
        if (
            !document.HasMember("latitude") ||
            !document["latitude"].IsNumber() ||
            !document.HasMember("longitude") ||
            !document["longitude"].IsNumber()
        ) {
            std::cerr << "set_position missing latitude or longitude\n";

            return std::nullopt;
        }

        command.latitude  = document["latitude"].GetDouble();
        command.longitude = document["longitude"].GetDouble();

        return command;
    }

    std::cerr
        << "Unknown map command: "
        << command.command
        << '\n';

    return std::nullopt;
}
