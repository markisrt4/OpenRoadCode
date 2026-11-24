// SPDX-License-Identifier: MIT
#pragma once

#include <rapidjson/document.h>
#include <rapidjson/stringbuffer.h>
#include <rapidjson/writer.h>
#include <stdexcept>
#include <string>

/** Add a dedicated aircraft layer without modifying existing map overlays. */
inline std::string withAircraftStyle(const std::string& style) {
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
        {"id":"aircraft-points","type":"circle","source":"aircraft",
         "paint":{"circle-radius":7,"circle-color":"#27d4ed",
                  "circle-stroke-color":"#10202b","circle-stroke-width":2}},
        {"id":"aircraft-headings","type":"symbol","source":"aircraft",
         "layout":{"text-field":"▲","text-size":16,
                   "text-font":["KlokanTech Noto Sans CJK Regular"],
                   "text-rotate":["coalesce",["get","heading_deg"],0],
                   "text-rotation-alignment":"map",
                   "text-allow-overlap":true},
         "paint":{"text-color":"#ffffff","text-halo-color":"#10202b","text-halo-width":1}},
        {"id":"aircraft-labels","type":"symbol","source":"aircraft",
         "layout":{"text-field":["coalesce",["get","callsign"],["get","icao"]],
                   "text-size":11,"text-font":["KlokanTech Noto Sans CJK Regular"],
                   "text-anchor":"top","text-offset":[0,1.2]},
         "paint":{"text-color":"#ffffff","text-halo-color":"#10202b","text-halo-width":2}}
      ]})");
    auto& allocator = document.GetAllocator();
    if (!document["sources"].HasMember("aircraft")) {
        rapidjson::Value source;
        source.CopyFrom(additions["source"], allocator);
        document["sources"].AddMember("aircraft", source, allocator);
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
