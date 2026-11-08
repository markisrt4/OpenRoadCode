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
    addition.Parse(R"({"id":"poi-results-brand","type":"symbol","source":"poi-results","minzoom":13,
      "filter":["has","brand_icon"],"layout":{"icon-image":["get","brand_icon"],
      "icon-size":0.7,"icon-allow-overlap":false,"icon-ignore-placement":false}})");
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
        rapidjson::Value copy; copy.CopyFrom(layer, allocator); result.PushBack(copy, allocator);
    }
    if (!inserted) { rapidjson::Value copy; copy.CopyFrom(addition, allocator); result.PushBack(copy, allocator); }
    layers = std::move(result);
    rapidjson::StringBuffer buffer;
    rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
    document.Accept(writer);
    return buffer.GetString();
}
