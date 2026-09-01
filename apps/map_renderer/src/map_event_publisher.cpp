// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT

#include "map_event_publisher.hpp"

#include <rapidjson/document.h>
#include <rapidjson/stringbuffer.h>
#include <rapidjson/writer.h>
#include <utility>

namespace { constexpr const char* kPoiSelectedTopic = "map.poi.selected"; }

MapEventPublisher::MapEventPublisher(std::string endpoint)
{
    socket.set(zmq::sockopt::linger, 0);
    socket.connect(std::move(endpoint));
}

void MapEventPublisher::publishPoiSelected(
    const std::string& name,
    const std::string& brand,
    const std::string& sourceClass,
    const std::string& sourceSubclass,
    double latitude,
    double longitude)
{
    rapidjson::Document document;
    document.SetObject();
    auto& allocator = document.GetAllocator();
    document.AddMember("name", rapidjson::Value(name.c_str(), allocator), allocator);
    document.AddMember("brand", rapidjson::Value(brand.c_str(), allocator), allocator);
    document.AddMember("class", rapidjson::Value(sourceClass.c_str(), allocator), allocator);
    document.AddMember("subclass", rapidjson::Value(sourceSubclass.c_str(), allocator), allocator);
    document.AddMember("latitude", latitude, allocator);
    document.AddMember("longitude", longitude, allocator);

    rapidjson::StringBuffer buffer;
    rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
    document.Accept(writer);
    socket.send(zmq::buffer(kPoiSelectedTopic), zmq::send_flags::sndmore);
    socket.send(zmq::buffer(buffer.GetString(), buffer.GetSize()), zmq::send_flags::none);
}
