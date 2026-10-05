// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT
#pragma once

#include <rapidjson/document.h>
#include <rapidjson/stringbuffer.h>
#include <rapidjson/writer.h>
#include <stdexcept>
#include <string>

/** @brief Add independent route forecast markers to any configured map style. */
inline std::string withRouteWeatherStyle(const std::string& style) {
    rapidjson::Document document;
    document.Parse(style.c_str());
    if (document.HasParseError() || !document.IsObject() ||
        !document.HasMember("sources") || !document["sources"].IsObject() ||
        !document.HasMember("layers") || !document["layers"].IsArray()) {
        throw std::runtime_error("map style has invalid sources or layers");
    }
    rapidjson::Document additions;
    additions.Parse(R"({
      "source":{"type":"geojson","data":{"type":"FeatureCollection","features":[]}},
      "layers":[
        {"id":"route-weather-points","type":"circle","source":"route-weather",
         "paint":{"circle-radius":6,"circle-color":"#a879ff",
                  "circle-stroke-color":"#ffffff","circle-stroke-width":2}},
        {"id":"route-weather-labels","type":"symbol","source":"route-weather",
         "layout":{"text-field":["get","label"],"text-size":12,
                   "text-font":["KlokanTech Noto Sans CJK Regular"],
                   "text-anchor":"top","text-offset":[0,0.8]},
         "paint":{"text-color":"#ffffff","text-halo-color":"#141d26","text-halo-width":2}}
      ]})");
    auto& allocator = document.GetAllocator();
    if (!document["sources"].HasMember("route-weather")) {
        rapidjson::Value source;
        source.CopyFrom(additions["source"], allocator);
        document["sources"].AddMember("route-weather", source, allocator);
        for (const auto& layer : additions["layers"].GetArray()) {
            rapidjson::Value copy;
            copy.CopyFrom(layer, allocator);
            document["layers"].PushBack(copy, allocator);
        }
    }
    rapidjson::StringBuffer buffer;
    rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
    document.Accept(writer);
    return buffer.GetString();
}
