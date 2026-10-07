// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT
#pragma once

#include <string>

// Match actual rendered weather features rather than a geographic proximity guess.
template <typename Properties>
std::string weatherCityHitId(const Properties& properties) {
    const auto city = properties.find("weather_city_id");
    if (city == properties.end() || !city->second.template is<std::string>())
        return {};
    const auto identity = city->second.template get<std::string>();
    return identity.rfind("weather-city:", 0) == 0 ? identity : std::string{};
}
