// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT
#include "../src/weather_city_hover.hpp"
#include "../src/city_weather_style.hpp"
#include <cassert>
#include <iostream>

int main() {
    WeatherCityHover hover;
    const std::string cities = R"({"type":"FeatureCollection","features":[
      {"type":"Feature","geometry":{"type":"Point","coordinates":[-83,42]},
       "properties":{"weather_city_id":"weather-city:Detroit","name":"Detroit","value":"50°F","color":"#ffffff"}},
      {"type":"Feature","geometry":{"type":"Point","coordinates":[-84,43]},
       "properties":{"weather_city_id":"weather-city:Lansing","name":"Lansing","value":"48°F","color":"#ffffff"}}]})";
    assert(!hover.setData(cities));
    assert(hover.select("weather-city:Detroit"));
    assert(hover.data().find("Detroit") != std::string::npos);
    assert(hover.data().find("Lansing") == std::string::npos);
    assert(hover.data().find("weather_city_hover") != std::string::npos);
    assert(!hover.select("weather-city:Detroit"));
    assert(hover.select("weather-city:Lansing"));
    assert(hover.data().find("Detroit") == std::string::npos);
    assert(hover.setData(R"({"type":"FeatureCollection","features":[]})"));
    assert(hover.data().find("Lansing") == std::string::npos);
    assert(!hover.select("weather-city:missing"));
    hover.setData(cities);
    hover.select("weather-city:Detroit");
    auto updated = cities;
    updated.replace(updated.find("50°F"), std::string("50°F").size(), "51°F");
    assert(hover.setData(updated));
    assert(hover.data().find("51°F") != std::string::npos);
    assert(hover.select(""));
    assert(hover.data() == R"({"type":"FeatureCollection","features":[]})");
    assert(!hover.setData("invalid JSON"));
    const auto style = withCityWeatherStyle(R"({"version":8,"sources":{},"layers":[]})");
    assert(withCityWeatherStyle(style) == style);
    rapidjson::Document parsed;
    parsed.Parse(style.c_str());
    assert(!parsed.HasParseError());
    assert(parsed["sources"].HasMember("city-weather-hover"));
    assert(parsed["layers"].Size() == 4);
    // Existing city styles must receive hover layers without duplicating their originals.
    parsed["sources"].RemoveMember("city-weather-hover");
    parsed["layers"].PopBack(); parsed["layers"].PopBack();
    rapidjson::StringBuffer oldBuffer;
    rapidjson::Writer<rapidjson::StringBuffer> writer(oldBuffer);
    parsed.Accept(writer);
    const auto upgraded = withCityWeatherStyle(oldBuffer.GetString());
    assert(withCityWeatherStyle(upgraded) == upgraded);
    std::cout << style;
}
