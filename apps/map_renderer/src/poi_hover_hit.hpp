// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT
#pragma once
#include <string>

// Only currently displayed search results may acquire a POI hover highlight.
template <typename Properties, typename Markers>
std::string poiHoverHitId(const Properties& properties, const Markers& markers) {
    const auto id = properties.find("id");
    if (id == properties.end() || !id->second.template is<std::string>()) return {};
    const auto candidate = id->second.template get<std::string>();
    if (candidate.empty()) return {};
    for (const auto& marker : markers)
        if (marker.id == candidate) return candidate;
    return {};
}
