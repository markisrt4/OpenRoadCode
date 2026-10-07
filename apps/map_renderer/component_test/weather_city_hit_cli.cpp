// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT

#include "../src/weather_city_hit.hpp"
#include <cassert>
#include <map>
#include <variant>
struct Value {
    std::variant<std::string, int> value;
    template <typename T> bool is() const { return std::holds_alternative<T>(value); }
    template <typename T> T get() const { return std::get<T>(value); }
};
int main() {
    std::map<std::string, Value> properties;
    assert(weatherCityHitId(properties).empty());
    properties["weather_city_id"] = Value{42};
    assert(weatherCityHitId(properties).empty());
    properties["weather_city_id"] = Value{std::string("poi:other")};
    assert(weatherCityHitId(properties).empty());
    properties["weather_city_id"] = Value{std::string("weather-city:Detroit:42.33000:-83.05000")};
    assert(weatherCityHitId(properties) == "weather-city:Detroit:42.33000:-83.05000");
}
