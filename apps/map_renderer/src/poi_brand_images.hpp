// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT
#pragma once
#include "poi_brand_payload.hpp"
#include <mbgl/style/image.hpp>
#include <mbgl/style/style.hpp>
#include <mbgl/util/image.hpp>
#include <memory>

inline std::string preparePoiBrandResults(mbgl::style::Style& style, const std::string& geojson) {
    for (const auto& [id, data] : poiBrandImages(geojson)) {
        if (style.getImage(id)) continue;
        try {
            style.addImage(std::make_unique<mbgl::style::Image>(id, mbgl::decodeImage(data), 2.0f));
        } catch (const std::exception&) {
            // Keep the category badge when an optional logo cannot be decoded.
        }
    }
    return withPoiBrandAvailability(geojson, [&style](const std::string& id) {
        return style.getImage(id).has_value();
    });
}
