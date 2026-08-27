// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT

#include "map_command_server.hpp"

#include <rapidjson/document.h>
#include <rapidjson/stringbuffer.h>
#include <rapidjson/writer.h>

#include <iostream>
#include <utility>

MapCommandServer::MapCommandServer(std::string endpoint_)
    : endpoint(std::move(endpoint_))
{
    socket.set(zmq::sockopt::linger, 0);
    socket.bind(endpoint);
    std::cout << "Map command endpoint: " << endpoint << '\n';
}

std::optional<MapCommand> MapCommandServer::poll()
{
    zmq::message_t request;
    const auto received = socket.recv(request, zmq::recv_flags::dontwait);
    if (!received) {
        return std::nullopt;
    }

    const std::string payload(
        static_cast<const char*>(request.data()), request.size()
    );
    const auto command = parseCommand(payload);
    if (!command) {
        sendReply(false, "Invalid map renderer command");
        return std::nullopt;
    }

    sendReply(true, "Command accepted");
    return command;
}

void MapCommandServer::sendReply(bool ok, const std::string& message)
{
    rapidjson::Document document;
    document.SetObject();
    auto& allocator = document.GetAllocator();
    document.AddMember("ok", ok, allocator);
    rapidjson::Value messageValue;
    messageValue.SetString(message.c_str(),
                           static_cast<rapidjson::SizeType>(message.size()),
                           allocator);
    document.AddMember("message", messageValue, allocator);

    rapidjson::StringBuffer buffer;
    rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
    document.Accept(writer);
    socket.send(zmq::buffer(buffer.GetString(), buffer.GetSize()),
                zmq::send_flags::none);
}

std::optional<MapCommand> MapCommandServer::parseCommand(
    const std::string& payload
) const
{
    rapidjson::Document document;
    document.Parse(payload.c_str());

    if (document.HasParseError() || !document.IsObject() ||
        !document.HasMember("command") || !document["command"].IsString()) {
        return std::nullopt;
    }

    MapCommand command;
    command.command = document["command"].GetString();

    if (command.command == "set_route") {
        if (!document.HasMember("geojson") || !document["geojson"].IsObject()) {
            return std::nullopt;
        }
        rapidjson::StringBuffer buffer;
        rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
        document["geojson"].Accept(writer);
        command.geojson = buffer.GetString();
        return command;
    }

    if (command.command == "set_center" || command.command == "set_position") {
        if (!document.HasMember("latitude") || !document["latitude"].IsNumber() ||
            !document.HasMember("longitude") || !document["longitude"].IsNumber()) {
            return std::nullopt;
        }
        command.latitude = document["latitude"].GetDouble();
        command.longitude = document["longitude"].GetDouble();
        return command;
    }

    if (command.command == "set_camera") {
        if (!document.HasMember("latitude") || !document["latitude"].IsNumber() ||
            !document.HasMember("longitude") || !document["longitude"].IsNumber() ||
            !document.HasMember("zoom") || !document["zoom"].IsNumber() ||
            !document.HasMember("bearing") || !document["bearing"].IsNumber() ||
            !document.HasMember("pitch") || !document["pitch"].IsNumber()) {
            return std::nullopt;
        }
        command.latitude = document["latitude"].GetDouble();
        command.longitude = document["longitude"].GetDouble();
        command.zoom = document["zoom"].GetDouble();
        command.bearing = document["bearing"].GetDouble();
        command.pitch = document["pitch"].GetDouble();
        return command;
    }

    if (command.command == "fit_bounds") {
        if (!document.HasMember("south") || !document["south"].IsNumber() ||
            !document.HasMember("west") || !document["west"].IsNumber() ||
            !document.HasMember("north") || !document["north"].IsNumber() ||
            !document.HasMember("east") || !document["east"].IsNumber()) {
            return std::nullopt;
        }
        command.south = document["south"].GetDouble();
        command.west = document["west"].GetDouble();
        command.north = document["north"].GetDouble();
        command.east = document["east"].GetDouble();
        if (document.HasMember("padding") && document["padding"].IsNumber()) {
            command.padding = document["padding"].GetDouble();
        }
        return command;
    }

    std::cerr << "Unknown map command: " << command.command << '\n';
    return std::nullopt;
}
