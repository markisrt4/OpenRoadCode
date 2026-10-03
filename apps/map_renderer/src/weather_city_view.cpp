// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT

#include "map_view.hpp"
#include "map_renderer_frontend.hpp"
#include "weather_city_selection.hpp"
#include <mbgl/renderer/renderer.hpp>
#include <mbgl/renderer/query.hpp>
#include <rapidjson/document.h>
#include <rapidjson/stringbuffer.h>
#include <rapidjson/writer.h>
#include <cmath>
#include <cstdint>
#include <utility>
#include <optional>

namespace {
std::string cityProperty(const mbgl::Feature& feature, const char* key) {
    const auto it = feature.properties.find(key);
    return it != feature.properties.end() && it->second.is<std::string>()
        ? it->second.get<std::string>() : "";
}
double cityRank(const mbgl::Feature& feature) {
    const auto it = feature.properties.find("rank");
    if (it == feature.properties.end()) return 50;
    const auto& value = it->second;
    if (value.is<uint64_t>()) return static_cast<double>(value.get<uint64_t>());
    if (value.is<int64_t>()) return static_cast<double>(value.get<int64_t>());
    if (value.is<double>() && std::isfinite(value.get<double>())) return value.get<double>();
    return 50;
}
}

std::string MapView::searchWeatherCities() const {
    rapidjson::Document cities;
    cities.SetArray();
    auto& allocator = cities.GetAllocator();
    if (map && rendererFrontend && rendererFrontend->getRenderer()) {
        const mbgl::SourceQueryOptions options{{{"place"}}, {}};
        const auto features = rendererFrontend->getRenderer()->querySourceFeatures("openroad", options);
        std::vector<WeatherCityCandidate> candidates;
        for (const auto& feature : features) {
            const auto type = cityProperty(feature, "class");
            double priority = type == "city" ? 0 : type == "town" ? 100 :
                              type == "village" ? 200 : type == "hamlet" ? 300 : -1;
            if (priority < 0) continue;
            auto name = cityProperty(feature, "name:latin");
            if (name.empty()) name = cityProperty(feature, "name");
            if (name.empty() || name.size() > 160) continue;
            const auto point = feature.geometry.match(
                [](const mapbox::geometry::point<double>& p) -> std::optional<mbgl::LatLng> {
                    return mbgl::LatLng{p.y, p.x};
                }, [](const auto&) -> std::optional<mbgl::LatLng> { return std::nullopt; });
            if (!point) continue;
            const auto pixel = map->pixelForLatLng(*point);
            // Leave room for the value and name above each city dot. Pixel-space
            // checks stay accurate when the map is rotated or tilted.
            if (pixel.x < 55 || pixel.x > width - 55 || pixel.y < 60 || pixel.y > height - 10) continue;
            candidates.push_back({name, point->latitude(), point->longitude(), pixel.x, pixel.y,
                                  priority + cityRank(feature)});
        }
        for (const auto& city : selectWeatherCities(std::move(candidates))) {
            rapidjson::Value item(rapidjson::kObjectType);
            item.AddMember("name", rapidjson::Value(city.name.c_str(), allocator), allocator);
            item.AddMember("latitude", city.latitude, allocator);
            item.AddMember("longitude", city.longitude, allocator);
            cities.PushBack(item, allocator);
        }
    }
    rapidjson::StringBuffer buffer;
    rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
    cities.Accept(writer);
    return buffer.GetString();
}
