// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT
#pragma once

#include <rapidjson/document.h>
#include <rapidjson/stringbuffer.h>
#include <rapidjson/writer.h>
#include <stdexcept>
#include <string>

/** Upgrade installed styles at runtime, without rebuilding the map dataset. */
inline std::string withVehicleStyle(const std::string& style) {
    rapidjson::Document document;
    document.Parse(style.c_str());
    if (document.HasParseError() || !document.IsObject() ||
        !document.HasMember("sources") || !document["sources"].IsObject() ||
        !document.HasMember("layers") || !document["layers"].IsArray())
        throw std::runtime_error("map style has invalid sources or layers");
    auto& layers = document["layers"];
    for (auto it = layers.Begin(); it != layers.End();) {
        if (it->HasMember("id") && (*it)["id"].IsString()) {
            const std::string id = (*it)["id"].GetString();
            if (id == "vehicle-heading" || id == "vehicle-veloster" ||
                id == "vehicle-orc-chevron" || id == "vehicle-position-unknown") {
                it = layers.Erase(it);
                continue;
            }
        }
        ++it;
    }
    rapidjson::Document additions;
    additions.Parse(R"({"layers":[
      {"id":"vehicle-position-unknown","type":"circle","source":"vehicle",
       "filter":["all",["!=",["get","marker_mode"],"blue_dot"],
                        ["!",["get","heading_known"]]],
       "paint":{"circle-radius":["*",7,["get","marker_scale"]],
                "circle-color":"#168bd1","circle-stroke-color":"#ffffff","circle-stroke-width":2}},
      {"id":"vehicle-orc-chevron","type":"symbol","source":"vehicle",
       "filter":["all",["!=",["get","marker_mode"],"blue_dot"],["get","heading_known"]],
       "layout":{"icon-image":"orc-vehicle-chevron","icon-size":["get","marker_scale"],
                 "icon-rotate":["get","heading"],"icon-rotation-alignment":"map",
                 "icon-pitch-alignment":"viewport","icon-allow-overlap":true,
                 "icon-ignore-placement":true}}
    ]})");
    auto& allocator = document.GetAllocator();
    if (!document["sources"].HasMember("vehicle")) {
        rapidjson::Document source;
        source.Parse(R"({"type":"geojson","data":{"type":"FeatureCollection","features":[]}})");
        rapidjson::Value copy;
        copy.CopyFrom(source, allocator);
        document["sources"].AddMember("vehicle", copy, allocator);
    }
    for (const auto& layer : additions["layers"].GetArray()) {
        rapidjson::Value copy;
        copy.CopyFrom(layer, allocator);
        layers.PushBack(copy, allocator);
    }
    rapidjson::StringBuffer buffer;
    rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
    document.Accept(writer);
    return buffer.GetString();
}
