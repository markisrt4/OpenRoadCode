// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT
#include "../src/map_feature_hover.hpp"
#include "../src/poi_hover_style.hpp"
#include "../src/poi_hover_hit.hpp"
#include "../src/city_weather_style.hpp"
#include <cassert>
#include <fstream>
#include <iostream>
#include <iterator>
#include <map>
#include <variant>
#include <vector>

struct HitValue {
    std::variant<std::string, int> value;
    template <typename T> bool is() const { return std::holds_alternative<T>(value); }
    template <typename T> T get() const { return std::get<T>(value); }
};
struct Marker { std::string id; };

int main(int argc, char** argv) {
    std::map<std::string, HitValue> properties;
    std::vector<Marker> markers{{"food-1"}};
    assert(poiHoverHitId(properties, markers).empty());
    properties["id"] = HitValue{42};
    assert(poiHoverHitId(properties, markers).empty());
    properties["id"] = HitValue{std::string("old-id")};
    assert(poiHoverHitId(properties, markers).empty());
    properties["id"] = HitValue{std::string("food-1")};
    assert(poiHoverHitId(properties, markers) == "food-1");
    markers.clear();
    assert(poiHoverHitId(properties, markers).empty());
    assert(argc == 2);
    MapFeatureHover hover{"id", "", "poi_hover"};
    const auto pois = R"({"type":"FeatureCollection","features":[
      {"type":"Feature","geometry":{"type":"Point","coordinates":[-83,42]},
       "properties":{"id":"food-1","name":"Cafe","category":"food"}},
      {"type":"Feature","geometry":{"type":"Point","coordinates":[-84,43]},
       "properties":{"id":"fuel-1","name":"Fuel","category":"fuel"}}]})";
    assert(!hover.setData(pois));
    assert(hover.select("food-1"));
    assert(hover.data().find("Cafe") != std::string::npos);
    assert(hover.data().find("Fuel") == std::string::npos);
    assert(hover.data().find("poi_hover") != std::string::npos);
    assert(!hover.select("food-1"));
    assert(hover.select("fuel-1"));
    assert(hover.data().find("Cafe") == std::string::npos);
    assert(hover.select(""));
    hover.select("food-1");
    assert(hover.setData(R"({"type":"FeatureCollection","features":[]})"));
    assert(hover.data().find("Cafe") == std::string::npos);
    assert(!hover.select("old-id"));
    std::ifstream input(argv[1]);
    const std::string original{std::istreambuf_iterator<char>{input}, {}};
    const auto style = withCityWeatherStyle(withPoiHoverStyle(original));
    assert(withCityWeatherStyle(withPoiHoverStyle(style)) == style);
    rapidjson::Document parsed;
    parsed.Parse(style.c_str());
    assert(!parsed.HasParseError());
    assert(parsed["sources"].HasMember("poi-hover"));
    std::size_t glow = 0, badge = 0;
    for (rapidjson::SizeType i = 0; i < parsed["layers"].Size(); ++i) {
        const std::string id = parsed["layers"][i]["id"].GetString();
        if (id == "poi-hover-glow") glow = i;
        if (id == "poi-results-badge") badge = i;
    }
    assert(glow < badge); // Preserve category badges/icons above the glow.
    std::cout << style;
}
