// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT
#pragma once

#include <rapidjson/document.h>
#include <rapidjson/stringbuffer.h>
#include <rapidjson/writer.h>
#include <string>

// Keep hover local to the renderer. The existing city identities remain the click contract.
class WeatherCityHover {
public:
    bool setData(const std::string& data) {
        cities = data;
        return select(identity);
    }

    bool select(const std::string& candidate) {
        rapidjson::Document input;
        input.Parse(cities.c_str());
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
                if (!properties.HasMember("weather_city_id") || !properties["weather_city_id"].IsString() ||
                    candidate != properties["weather_city_id"].GetString() || candidate.rfind("weather-city:", 0) != 0)
                    continue;
                rapidjson::Value copy;
                copy.CopyFrom(feature, allocator);
                copy["properties"].RemoveMember("weather_city_hover");
                copy["properties"].AddMember("weather_city_hover", true, allocator);
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
    std::string cities = R"({"type":"FeatureCollection","features":[]})";
    std::string identity;
    std::string geojson = R"({"type":"FeatureCollection","features":[]})";
};
