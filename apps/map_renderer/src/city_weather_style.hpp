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
         "paint":{"text-color":["get","color"],"text-halo-color":"#101820","text-halo-width":2}},
        {"id":"city-weather-hover-glow","type":"circle","source":"city-weather-hover",
         "paint":{"circle-radius":13,"circle-color":"#fff3a6","circle-opacity":0.75,"circle-blur":0.8}},
        {"id":"city-weather-hover-label","type":"symbol","source":"city-weather-hover",
         "layout":{"text-field":["format",["get","value"],{"font-scale":1.8},
                    "\n",{},["get","name"],{"font-scale":0.9}],
                   "text-size":14,"text-font":["KlokanTech Noto Sans CJK Regular"],
                   "text-anchor":"bottom","text-offset":[0,-0.6],
                   "text-allow-overlap":true,"text-ignore-placement":true},
         "paint":{"text-color":"#fffbd9","text-halo-color":"#e6bd4d",
                  "text-halo-width":4,"text-halo-blur":2}}
      ]})");
    auto& allocator = document.GetAllocator();
    for (const char* sourceId : {"city-weather", "city-weather-hover"}) {
        if (!document["sources"].HasMember(sourceId)) {
            rapidjson::Value source;
            source.CopyFrom(additions["source"], allocator);
            document["sources"].AddMember(rapidjson::Value(sourceId, allocator), source, allocator);
        }
    }
    for (const auto& layer : additions["layers"].GetArray()) {
        bool exists = false;
        for (const auto& installed : document["layers"].GetArray()) {
            if (installed.IsObject() && installed.HasMember("id") && installed["id"].IsString() &&
                std::string(installed["id"].GetString()) == layer["id"].GetString()) {
                exists = true;
                break;
            }
        }
        if (!exists) {
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
