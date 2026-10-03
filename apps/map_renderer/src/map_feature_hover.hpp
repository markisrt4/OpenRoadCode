// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT
#pragma once

#include <rapidjson/document.h>
#include <rapidjson/stringbuffer.h>
#include <rapidjson/writer.h>
#include <string>
#include <utility>

// Keep hover local to the renderer, using identities from the existing click contracts.
class MapFeatureHover {
public:
    explicit MapFeatureHover(std::string property = "weather_city_id",
                             std::string prefix = "weather-city:",
                             std::string flag = "weather_city_hover")
        : identityProperty(std::move(property)), identityPrefix(std::move(prefix)), hoverFlag(std::move(flag)) {}

    bool setData(const std::string& data) {
        featuresData = data;
        return select(identity);
    }

    bool select(const std::string& candidate) {
        rapidjson::Document input;
        input.Parse(featuresData.c_str());
        rapidjson::Document output;
        output.SetObject();
        auto& allocator = output.GetAllocator();
        output.AddMember("type", "FeatureCollection", allocator);
        rapidjson::Value features(rapidjson::kArrayType);
        std::string matched;
        if (!candidate.empty() && !input.HasParseError() && input.IsObject() &&
            input.HasMember("features") && input["features"].IsArray()) {
            for (const auto& feature : input["features"].GetArray()) {
                if (!feature.IsObject() || !feature.HasMember("properties") || !feature["properties"].IsObject())
                    continue;
                const auto& properties = feature["properties"];
                if (!properties.HasMember(identityProperty.c_str()) || !properties[identityProperty.c_str()].IsString() ||
                    candidate != properties[identityProperty.c_str()].GetString() || candidate.rfind(identityPrefix, 0) != 0)
                    continue;
                rapidjson::Value copy;
                copy.CopyFrom(feature, allocator);
                copy["properties"].RemoveMember(hoverFlag.c_str());
                copy["properties"].AddMember(rapidjson::Value(hoverFlag.c_str(), allocator), rapidjson::Value(true), allocator);
                features.PushBack(copy, allocator);
                matched = candidate;
                break;
            }
        }
        output.AddMember("features", features, allocator);
        rapidjson::StringBuffer buffer;
        rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
        output.Accept(writer);
        const std::string next = buffer.GetString();
        identity = matched;
        if (next == geojson)
            return false;
        geojson = next;
        return true;
    }

    const std::string& data() const { return geojson; }

private:
    std::string identityProperty, identityPrefix, hoverFlag;
    std::string featuresData = R"({"type":"FeatureCollection","features":[]})";
    std::string identity;
    std::string geojson = R"({"type":"FeatureCollection","features":[]})";
};
