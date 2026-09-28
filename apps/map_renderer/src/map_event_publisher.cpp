// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT

#include "map_event_publisher.hpp"

#include <rapidjson/document.h>
#include <rapidjson/stringbuffer.h>
#include <rapidjson/writer.h>
#include <utility>
#include <limits>

namespace {
constexpr const char* kPoiSelectedTopic = "map.poi.selected";
constexpr const char* kPoiSearchResultTopic = "map.poi.search_result";
constexpr const char* kManualCameraTopic = "map.camera.manual";
constexpr const char* kMapClickTopic = "map.click";

std::string jsonString(rapidjson::Document& document)
{
    rapidjson::StringBuffer buffer;
    rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
    document.Accept(writer);
    return buffer.GetString();
}
}

MapEventPublisher::MapEventPublisher(std::string endpoint)
{
    socket.set(zmq::sockopt::linger, 0);
    socket.connect(std::move(endpoint));
}

void MapEventPublisher::publishJson(const char* topic, const std::string& json)
{
    socket.send(zmq::buffer(topic, std::char_traits<char>::length(topic)), zmq::send_flags::sndmore);
    socket.send(zmq::buffer(json), zmq::send_flags::none);
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
    publishJson(kPoiSelectedTopic, jsonString(document));
}

void MapEventPublisher::publishManualCameraInteraction()
{
    rapidjson::Document document;
    document.SetObject();
    publishJson(kManualCameraTopic, jsonString(document));
}

void MapEventPublisher::publishMapClick(
    double latitude,
    double longitude,
    double selectionRadiusM,
    const std::string& markerId,
    std::size_t markerIndex)
{
    rapidjson::Document document;
    document.SetObject();
    auto& allocator = document.GetAllocator();
    document.AddMember("latitude", latitude, allocator);
    document.AddMember("longitude", longitude, allocator);
    document.AddMember("selection_radius_m", selectionRadiusM, allocator);
    document.AddMember("marker_id", rapidjson::Value(markerId.c_str(), allocator), allocator);
    if (markerIndex != std::numeric_limits<std::size_t>::max()) {
        document.AddMember("marker_index", static_cast<uint64_t>(markerIndex), allocator);
    }
    publishJson(kMapClickTopic, jsonString(document));
}

void MapEventPublisher::publishPoiSearchResult(
    const std::string& category,
    int count,
    double south,
    double west,
    double north,
    double east)
{
    rapidjson::Document document;
    document.SetObject();
    auto& allocator = document.GetAllocator();
    document.AddMember("category", rapidjson::Value(category.c_str(), allocator), allocator);
    document.AddMember("count", count, allocator);
    document.AddMember("south", south, allocator);
    document.AddMember("west", west, allocator);
    document.AddMember("north", north, allocator);
    document.AddMember("east", east, allocator);
    publishJson(kPoiSearchResultTopic, jsonString(document));
}
