// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT

#pragma once

#include <string>

/** @brief Runtime configuration consumed by the native map renderer. */
struct NavigationConfig
{
    std::string stylePath{"/srv/openroadcode/maps/styles/openroadcode.json"};
    std::string cachePath{"/var/cache/openroadcode/maplibre.db"};
    std::string markerMode{"vehicle"};
    double markerScale{1.0};
};

/**
 * @brief Load native renderer settings from a navigation TOML file.
 * @param path Path to the navigation runtime configuration.
 * @return Parsed renderer and vehicle-marker settings.
 */
NavigationConfig loadNavigationConfig(
    const std::string& path = "/etc/openroadcode/navigation.toml"
);
