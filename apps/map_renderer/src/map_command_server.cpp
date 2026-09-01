// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT

#include "map_command_server.hpp"

#include <rapidjson/document.h>
#include <rapidjson/stringbuffer.h>
#include <rapidjson/writer.h>

#include <iostream>
#include <utility>

namespace { constexpr const char* kMapCommandTopic = "map.command"; }

MapCommandServer::MapCommandServer(std::string endpoint_) : endpoint(std::move(endpoint_))
{
    socket.set(zmq::sockopt::linger, 0);
    socket.set(zmq::sockopt::subscribe, kMapCommandTopic);
    socket.connect(endpoint);
    std::cout << "Map command bus: " << endpoint << " topic=" << kMapCommandTopic << '\n';
}

std::optional<MapCommand> MapCommandServer::poll()
{
    zmq::message_t topicMessage;
    if (!socket.recv(topicMessage, zmq::recv_flags::dontwait)) return std::nullopt;
    zmq::message_t payloadMessage;
    if (!socket.recv(payloadMessage, zmq::recv_flags::none)) return std::nullopt;
    const std::string topic(static_cast<const char*>(topicMessage.data()), topicMessage.size());
    if (topic != kMapCommandTopic) return std::nullopt;
    const std::string payload(static_cast<const char*>(payloadMessage.data()), payloadMessage.size());
    const auto command = parseCommand(payload);
    if (!command) std::cerr << "[map_renderer] invalid map.command payload\n";
    return command;
}

std::optional<MapCommand> MapCommandServer::parseCommand(const std::string& payload) const
{
    rapidjson::Document document;
    document.Parse(payload.c_str());
    if (document.HasParseError() || !document.IsObject() || !document.HasMember("command") ||
        !document["command"].IsString()) return std::nullopt;

    MapCommand command;
    command.command = document["command"].GetString();

    if (command.command == "set_route") {
        if (!document.HasMember("geojson") || !document["geojson"].IsObject()) return std::nullopt;
        rapidjson::StringBuffer buffer;
        rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
        document["geojson"].Accept(writer);
        command.geojson = buffer.GetString();
        return command;
    }
    if (command.command == "set_poi_focus" || command.command == "search_pois") {
        if (!document.HasMember("category") || !document["category"].IsString()) return std::nullopt;
        command.category = document["category"].GetString();
        command.enabled = document.HasMember("enabled") && document["enabled"].IsBool()
            ? document["enabled"].GetBool() : !command.category.empty();
        return command;
    }
    if (command.command == "set_center" || command.command == "set_position") {
        if (!document.HasMember("latitude") || !document["latitude"].IsNumber() ||
            !document.HasMember("longitude") || !document["longitude"].IsNumber()) return std::nullopt;
        command.latitude = document["latitude"].GetDouble();
        command.longitude = document["longitude"].GetDouble();
        return command;
    }
    if (command.command == "set_camera") {
        if (!document.HasMember("latitude") || !document["latitude"].IsNumber() ||
            !document.HasMember("longitude") || !document["longitude"].IsNumber() ||
            !document.HasMember("zoom") || !document["zoom"].IsNumber() ||
            !document.HasMember("bearing") || !document["bearing"].IsNumber() ||
            !document.HasMember("pitch") || !document["pitch"].IsNumber()) return std::nullopt;
        command.latitude = document["latitude"].GetDouble(); command.longitude = document["longitude"].GetDouble();
        command.zoom = document["zoom"].GetDouble(); command.bearing = document["bearing"].GetDouble();
        command.pitch = document["pitch"].GetDouble(); return command;
    }
    if (command.command == "fit_bounds") {
        if (!document.HasMember("south") || !document["south"].IsNumber() ||
            !document.HasMember("west") || !document["west"].IsNumber() ||
            !document.HasMember("north") || !document["north"].IsNumber() ||
            !document.HasMember("east") || !document["east"].IsNumber()) return std::nullopt;
        command.south = document["south"].GetDouble(); command.west = document["west"].GetDouble();
        command.north = document["north"].GetDouble(); command.east = document["east"].GetDouble();
        if (document.HasMember("padding") && document["padding"].IsNumber()) command.padding = document["padding"].GetDouble();
        return command;
    }
    std::cerr << "Unknown map command: " << command.command << '\n';
    return std::nullopt;
}
