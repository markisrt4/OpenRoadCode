// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT
#pragma once

#include <rapidjson/document.h>
#include <rapidjson/stringbuffer.h>
#include <rapidjson/writer.h>
#include <stdexcept>
#include <string>

inline std::string withPoiHoverStyle(const std::string& style) {
    rapidjson::Document document;
    document.Parse(style.c_str());
    if (document.HasParseError() || !document.IsObject() ||
        !document.HasMember("sources") || !document["sources"].IsObject() ||
        !document.HasMember("layers") || !document["layers"].IsArray())
        throw std::runtime_error("map style has invalid sources or layers");
    if (!document["sources"].HasMember("poi-results")) return style;
    rapidjson::Document additions;
    additions.Parse(R"({
      "source":{"type":"geojson","data":{"type":"FeatureCollection","features":[]}},
      "glow":{"id":"poi-hover-glow","type":"circle","source":"poi-hover","minzoom":7,
        "paint":{"circle-radius":["interpolate",["linear"],["zoom"],7,12,11,16,15,19],
                 "circle-color":"#fff3a6","circle-opacity":0.3,"circle-blur":0.8}},
      "label":{"id":"poi-hover-label","type":"symbol","source":"poi-hover","minzoom":9,
        "layout":{"text-field":"{name}","text-font":["KlokanTech Noto Sans CJK Regular"],
                  "text-size":["interpolate",["linear"],["zoom"],9,10,13,12,16,14],
                  "text-offset":[0,1.15],"text-anchor":"top",
                  "text-allow-overlap":true,"text-ignore-placement":true},
        "paint":{"text-color":"#fffbd9","text-halo-color":"#101820",
                 "text-halo-width":2,"text-halo-blur":0}}
    })");
    auto& allocator = document.GetAllocator();
    if (!document["sources"].HasMember("poi-hover")) {
        rapidjson::Value source;
        source.CopyFrom(additions["source"], allocator);
        document["sources"].AddMember("poi-hover", source, allocator);
    }
    bool hasGlow = false, hasLabel = false;
    for (const auto& layer : document["layers"].GetArray()) {
        if (!layer.IsObject() || !layer.HasMember("id") || !layer["id"].IsString()) continue;
        const std::string id = layer["id"].GetString();
        hasGlow |= id == "poi-hover-glow";
        hasLabel |= id == "poi-hover-label";
    }
    rapidjson::Value layers(rapidjson::kArrayType);
    for (const auto& layer : document["layers"].GetArray()) {
        if (!hasGlow && layer.IsObject() && layer.HasMember("id") && layer["id"].IsString() &&
            std::string(layer["id"].GetString()) == "poi-results-badge") {
            rapidjson::Value glow;
            glow.CopyFrom(additions["glow"], allocator);
            layers.PushBack(glow, allocator);
            hasGlow = true;
        }
        rapidjson::Value copy;
        copy.CopyFrom(layer, allocator);
        layers.PushBack(copy, allocator);
    }
    if (!hasGlow) {
        rapidjson::Value glow;
        glow.CopyFrom(additions["glow"], allocator);
        layers.PushBack(glow, allocator);
    }
    if (!hasLabel) {
        rapidjson::Value label;
        label.CopyFrom(additions["label"], allocator);
        layers.PushBack(label, allocator);
    }
    document["layers"] = std::move(layers);
    rapidjson::StringBuffer buffer;
    rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
    document.Accept(writer);
    return buffer.GetString();
}
