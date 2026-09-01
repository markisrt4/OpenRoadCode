// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT

#pragma once

#include <string>
#include <zmq.hpp>

class MapEventPublisher {
public:
    explicit MapEventPublisher(std::string endpoint);

    void publishPoiSelected(
        const std::string& name,
        const std::string& brand,
        const std::string& sourceClass,
        const std::string& sourceSubclass,
        double latitude,
        double longitude
    );

    void publishPoiSearchResult(
        const std::string& category,
        int count,
        double south,
        double west,
        double north,
        double east
    );

private:
    void publishJson(const char* topic, const std::string& json);
    zmq::context_t context{1};
    zmq::socket_t socket{context, zmq::socket_type::pub};
};
