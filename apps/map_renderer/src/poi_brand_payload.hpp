// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT
#pragma once
#include <rapidjson/document.h>
#include <algorithm>
#include <cstdint>
#include <optional>
#include <string>
#include <vector>
#include <utility>
#include <unordered_set>

inline std::optional<std::string> poiPngBytes(const std::string& encoded) {
    if (encoded.size() > 90000) return std::nullopt;
    const std::string alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    std::string data;
    std::uint32_t value = 0;
    int bits = -8;
    for (const unsigned char character : encoded) {
        if (character == '=') break;
        const auto index = alphabet.find(character);
        if (index == std::string::npos) return std::nullopt;
        value = (value << 6) | static_cast<std::uint32_t>(index);
        bits += 6;
        if (bits >= 0) { data.push_back(static_cast<char>((value >> bits) & 255)); bits -= 8; }
    }
    // Limit dimensions before decoding, not after allocation/decompression.
    if (data.size() < 24 || data.compare(0, 8, "\x89PNG\r\n\x1a\n", 8) != 0) return std::nullopt;
    auto dimension = [&data](std::size_t offset) {
        std::uint32_t result = 0;
        for (std::size_t i = offset; i < offset + 4; ++i)
            result = (result << 8) | static_cast<unsigned char>(data[i]);
        return result;
    };
    if (dimension(16) != 64 || dimension(20) != 64) return std::nullopt;
    return data;
}

inline std::vector<std::pair<std::string, std::string>> poiBrandImages(const std::string& geojson) {
    std::vector<std::pair<std::string, std::string>> images;
    std::unordered_set<std::string> seen;
    rapidjson::Document document;
    document.Parse(geojson.c_str());
    if (!document.IsObject() || !document.HasMember("features") || !document["features"].IsArray()) return images;
    std::size_t loaded = 0;
    for (const auto& feature : document["features"].GetArray()) {
        if (++loaded > 100) break;
        if (!feature.IsObject() || !feature.HasMember("properties") || !feature["properties"].IsObject()) continue;
        const auto& properties = feature["properties"];
        if (!properties.HasMember("brand_icon") || !properties["brand_icon"].IsString() ||
            !properties.HasMember("brand_icon_png") || !properties["brand_icon_png"].IsString()) continue;
        const std::string id = properties["brand_icon"].GetString();
        if (id.size() <= 9 || id.size() > 73 || id.rfind("business:", 0) != 0 ||
            !std::all_of(id.begin() + 9, id.end(), [](char c) { return (c >= 'a' && c <= 'z') ||
                (c >= '0' && c <= '9') || c == '-'; }) || !seen.insert(id).second) continue;
        const auto data = poiPngBytes(properties["brand_icon_png"].GetString());
        if (!data) continue;
        images.emplace_back(id, *data);
    }
    return images;
}
