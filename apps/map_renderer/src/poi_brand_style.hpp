// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT
#pragma once
#include <rapidjson/document.h>
#include <rapidjson/stringbuffer.h>
#include <rapidjson/writer.h>
#include <string>

inline std::string withPoiBrandStyle(const std::string& style) {
    rapidjson::Document document;
    document.Parse(style.c_str());
    if (!document.IsObject() || !document.HasMember("sources") ||
        !document["sources"].IsObject() || !document["sources"].HasMember("poi-results") ||
        !document.HasMember("layers") || !document["layers"].IsArray()) return style;
    for (const auto& layer : document["layers"].GetArray())
        if (layer.IsObject() && layer.HasMember("id") && layer["id"].IsString() &&
            std::string(layer["id"].GetString()) == "poi-results-brand") return style;
    rapidjson::Document addition;
    addition.Parse(R"({"id":"poi-results-brand","type":"symbol","source":"poi-results","minzoom":7,
      "filter":["==",["get","brand_icon_ready"],true],"layout":{"icon-image":["get","brand_icon"],
      "icon-size":["interpolate",["linear"],["zoom"],7,0.45,11,0.6,15,0.7],
      "icon-allow-overlap":true,"icon-ignore-placement":true}})");
    // Insert immediately before the result labels so labels stay legible.
    auto& allocator = document.GetAllocator();
    auto& layers = document["layers"];
    rapidjson::Value result(rapidjson::kArrayType);
    bool inserted = false;
    for (const auto& layer : layers.GetArray()) {
        if (!inserted && layer.IsObject() && layer.HasMember("id") && layer["id"].IsString() &&
            std::string(layer["id"].GetString()) == "poi-results-label") {
            rapidjson::Value copy; copy.CopyFrom(addition, allocator);
            result.PushBack(copy, allocator); inserted = true;
        }
        rapidjson::Value copy; copy.CopyFrom(layer, allocator);
        if (copy.IsObject() && copy.HasMember("id") && copy["id"].IsString()) {
            const std::string id = copy["id"].GetString();
            if (id == "poi-results-badge" || id == "poi-results-glow" || id == "poi-results-icon") {
                rapidjson::Document fallback;
                fallback.Parse(R"(["!=",["get","brand_icon_ready"],true])");
                rapidjson::Value filter;
                filter.CopyFrom(fallback, allocator);
                if (copy.HasMember("filter")) {
                    rapidjson::Value combined(rapidjson::kArrayType);
                    combined.PushBack(rapidjson::Value("all", allocator), allocator);
                    combined.PushBack(copy["filter"], allocator);
                    combined.PushBack(filter, allocator);
                    copy["filter"] = std::move(combined);
                } else copy.AddMember("filter", filter, allocator);
            }
        }
        result.PushBack(copy, allocator);
    }
    if (!inserted) { rapidjson::Value copy; copy.CopyFrom(addition, allocator); result.PushBack(copy, allocator); }
    layers = std::move(result);
    rapidjson::StringBuffer buffer;
    rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
    document.Accept(writer);
    return buffer.GetString();
}
