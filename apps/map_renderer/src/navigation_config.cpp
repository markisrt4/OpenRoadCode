// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT

#include "navigation_config.hpp"

#include <algorithm>
#include <cctype>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <stdexcept>
#include <string>

namespace {

std::string trim(std::string value)
{
    const auto notSpace = [](unsigned char c) { return !std::isspace(c); };
    value.erase(value.begin(), std::find_if(value.begin(), value.end(), notSpace));
    value.erase(std::find_if(value.rbegin(), value.rend(), notSpace).base(), value.end());
    return value;
}

std::string unquote(std::string value)
{
    value = trim(std::move(value));
    if (value.size() >= 2 && value.front() == '"' && value.back() == '"') {
        return value.substr(1, value.size() - 2);
    }
    return value;
}

bool validMarkerMode(const std::string& mode)
{
    return mode == "blue_dot" || mode == "heading" || mode == "vehicle";
}

std::string environmentOrDefault(const char* name, const std::string& fallback)
{
    const auto* configured = std::getenv(name);
    if (configured != nullptr && configured[0] != '\0') {
        return configured;
    }
    return fallback;
}

std::string resolvePath(const std::string& root, const std::string& path)
{
    const std::filesystem::path configured{path};
    if (configured.is_absolute()) {
        return configured.lexically_normal().string();
    }
    return (std::filesystem::path{root} / configured).lexically_normal().string();
}

} // namespace

NavigationConfig loadNavigationConfig(const std::string& path)
{
    NavigationConfig config;
    std::ifstream input(path);

    std::string section;
    std::string line;
    if (input) {
        while (std::getline(input, line)) {
            const auto comment = line.find('#');
            if (comment != std::string::npos) {
                line.erase(comment);
            }
            line = trim(std::move(line));
            if (line.empty()) {
                continue;
            }
            if (line.front() == '[' && line.back() == ']') {
                section = trim(line.substr(1, line.size() - 2));
                continue;
            }

            const auto equals = line.find('=');
            if (equals == std::string::npos) {
                continue;
            }
            const auto key = trim(line.substr(0, equals));
            const auto value = trim(line.substr(equals + 1));

            if (section == "map_renderer" && key == "data_root") {
                config.dataRoot = unquote(value);
            } else if (section == "map_renderer" && key == "cache_root") {
                config.cacheRoot = unquote(value);
            } else if (section == "map_renderer" && key == "style") {
                config.stylePath = unquote(value);
            } else if (section == "map_renderer" && key == "cache") {
                config.cachePath = unquote(value);
            } else if (section == "vehicle_marker" && key == "mode") {
                const auto mode = unquote(value);
                if (!validMarkerMode(mode)) {
                    throw std::runtime_error("unsupported vehicle marker mode: " + mode);
                }
                config.markerMode = mode;
            } else if (section == "vehicle_marker" && key == "scale") {
                config.markerScale = std::stod(value);
                if (config.markerScale <= 0.0) {
                    throw std::runtime_error("vehicle marker scale must be positive");
                }
            }
        }
    }

    config.dataRoot = environmentOrDefault("OPENROADCODE_DATA_ROOT", config.dataRoot);
    config.cacheRoot = environmentOrDefault("OPENROADCODE_CACHE_ROOT", config.cacheRoot);
    config.stylePath = resolvePath(config.dataRoot, config.stylePath);
    config.cachePath = resolvePath(config.cacheRoot, config.cachePath);
    return config;
}
