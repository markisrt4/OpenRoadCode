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

private:
    zmq::context_t context{1};
    zmq::socket_t socket{context, zmq::socket_type::pub};
};
