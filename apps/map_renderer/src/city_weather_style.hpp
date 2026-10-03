// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT
#pragma once

#include <rapidjson/document.h>
#include <rapidjson/stringbuffer.h>
#include <rapidjson/writer.h>
#include <stdexcept>
#include <string>

/** @brief Add large weather values with smaller city names above other map overlays. */
inline std::string withCityWeatherStyle(const std::string& style) {
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
        {"id":"city-weather-points","type":"circle","source":"city-weather",
         "paint":{"circle-radius":3,"circle-color":"#ffffff",
                  "circle-stroke-color":"#141d26","circle-stroke-width":1}},
        {"id":"city-weather-labels","type":"symbol","source":"city-weather",
         "layout":{"text-field":["format",["get","value"],{"font-scale":1.8},
                    "\n",{},["get","name"],{"font-scale":0.9}],
                   "text-size":14,"text-font":["KlokanTech Noto Sans CJK Regular"],
                   "text-anchor":"bottom","text-offset":[0,-0.6],
                   "text-allow-overlap":false},
         "paint":{"text-color":["get","color"],"text-halo-color":"#101820","text-halo-width":2}}
      ]})");
    auto& allocator = document.GetAllocator();
    if (!document["sources"].HasMember("city-weather")) {
        rapidjson::Value source;
        source.CopyFrom(additions["source"], allocator);
        document["sources"].AddMember("city-weather", source, allocator);
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
