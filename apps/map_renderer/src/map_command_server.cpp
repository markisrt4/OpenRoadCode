#include "map_command_server.hpp"

#include <rapidjson/document.h>

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


std::optional<SetCenterCommand>
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

    char buffer[4096];

    const ssize_t count =
        ::read(
            clientFd,
            buffer,
            sizeof(buffer) - 1
        );

    ::close(clientFd);

    if (count <= 0) {
        return std::nullopt;
    }

    buffer[count] = '\0';

    return parseCommand(
        std::string(buffer)
    );
}


std::optional<SetCenterCommand>
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

    const std::string command =
        document["command"].GetString();

    if (command != "set_center") {
        std::cerr
            << "Unknown map command: "
            << command
            << '\n';

        return std::nullopt;
    }

    if (
        !document.HasMember("latitude") ||
        !document["latitude"].IsNumber() ||
        !document.HasMember("longitude") ||
        !document["longitude"].IsNumber()
    ) {
        std::cerr
            << "set_center missing latitude "
               "or longitude\n";

        return std::nullopt;
    }

    return SetCenterCommand{
        document["latitude"].GetDouble(),
        document["longitude"].GetDouble()
    };
}
