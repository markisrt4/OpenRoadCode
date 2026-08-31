// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT

#include "map_renderer_frontend.hpp"
#include "map_view.hpp"
#include "map_command_server.hpp"
#include "navigation_config.hpp"

#include <mbgl/map/map.hpp>
#include <mbgl/renderer/renderer.hpp>
#include <mbgl/style/layer.hpp>
#include <mbgl/style/style.hpp>
#include <mbgl/style/sources/geojson_source.hpp>
#include <mapbox/geojson.hpp>

#include <cstdlib>
#include <fstream>
#include <iostream>
#include <iterator>
#include <memory>
#include <stdexcept>
#include <string>

namespace {
constexpr double kDefaultLatitude = 0.0;
constexpr double kDefaultLongitude = 0.0;
constexpr double kDefaultZoom = 2.0;
constexpr const char* kDefaultBrokerSubscriberEndpoint = "tcp://127.0.0.1:5557";
constexpr const char* kDataRootToken = "__OPENROADCODE_DATA_ROOT__";
constexpr const char* kLegacyDataRoot = "/srv/openroadcode";

std::string environmentOrDefault(const char* name, const char* fallback) {
    const auto* configured = std::getenv(name);
    return configured != nullptr && configured[0] != '\0' ? configured : fallback;
}
void replaceAll(std::string& value, const std::string& from, const std::string& to) {
    if (from.empty()) return;
    std::size_t offset = 0;
    while ((offset = value.find(from, offset)) != std::string::npos) {
        value.replace(offset, from.length(), to); offset += to.length();
    }
}
std::string loadStyleJson(const NavigationConfig& config) {
    std::ifstream input(config.stylePath);
    if (!input) throw std::runtime_error("unable to open map style: " + config.stylePath);
    std::string style{std::istreambuf_iterator<char>{input}, std::istreambuf_iterator<char>{}};
    replaceAll(style, kDataRootToken, config.dataRoot);
    if (config.dataRoot != kLegacyDataRoot) replaceAll(style, kLegacyDataRoot, config.dataRoot);
    return style;
}
void setLayerVisible(mbgl::style::Style& style, const char* id, bool visible) {
    auto* layer = style.getLayer(id);
    if (layer != nullptr) {
        layer->setVisibility(visible ? mbgl::style::VisibilityType::Visible
                                     : mbgl::style::VisibilityType::None);
    }
}
} // namespace

int main() {
    const auto configPath = environmentOrDefault("OPENROADCODE_NAVIGATION_CONFIG", "/etc/openroadcode/navigation.toml");
    const auto brokerSubscriberEndpoint = environmentOrDefault("OPENROADCODE_BROKER_SUBSCRIBER_ENDPOINT", kDefaultBrokerSubscriberEndpoint);
    NavigationConfig config;
    try { config = loadNavigationConfig(configPath); }
    catch (const std::exception& exception) { std::cerr << "[map_renderer] invalid navigation config: " << exception.what() << '\n'; return 1; }
    std::string styleJson;
    try { styleJson = loadStyleJson(config); }
    catch (const std::exception& exception) { std::cerr << "[map_renderer] failed to load navigation style: " << exception.what() << '\n'; return 1; }

    mbgl::ResourceOptions resourceOptions; resourceOptions.withCachePath(config.cachePath);
    mbgl::ClientOptions clientOptions;
    MapView view(resourceOptions, clientOptions);
    MapRendererFrontend rendererFrontend{std::make_unique<mbgl::Renderer>(view.getRendererBackend(), view.getPixelRatio()), view};
    mbgl::Map map(rendererFrontend, view, mbgl::MapOptions().withSize(view.getSize()).withPixelRatio(view.getPixelRatio()), resourceOptions, clientOptions);
    view.setMap(&map);
    map.jumpTo(mbgl::CameraOptions().withCenter(mbgl::LatLng{kDefaultLatitude, kDefaultLongitude}).withZoom(kDefaultZoom));
    MapCommandServer commandServer(brokerSubscriberEndpoint);

    view.setUpdateCallback([&map, &commandServer, &config]() {
        const auto command = commandServer.poll(); if (!command) return;
        if (command->command == "set_center") { map.jumpTo(mbgl::CameraOptions().withCenter(mbgl::LatLng{command->latitude, command->longitude})); return; }
        if (command->command == "fit_bounds") {
            const auto bounds = mbgl::LatLngBounds::hull(mbgl::LatLng{command->south, command->west}, mbgl::LatLng{command->north, command->east});
            const mbgl::EdgeInsets padding{command->padding, command->padding, command->padding, command->padding};
            map.easeTo(map.cameraForLatLngBounds(bounds, padding), mbgl::AnimationOptions{mbgl::Milliseconds(500)}); return;
        }
        if (command->command == "set_position") {
            auto* source = map.getStyle().getSource("vehicle"); if (!source) return;
            auto* vehicleSource = static_cast<mbgl::style::GeoJSONSource*>(source);
            mapbox::geojson::feature feature{mapbox::geojson::geometry{mapbox::geometry::point<double>{command->longitude, command->latitude}}};
            feature.properties["marker_mode"] = config.markerMode; feature.properties["marker_scale"] = config.markerScale;
            vehicleSource->setGeoJSON(feature); return;
        }
        if (command->command == "set_camera") {
            map.jumpTo(mbgl::CameraOptions().withCenter(mbgl::LatLng{command->latitude, command->longitude})
                .withZoom(command->zoom).withBearing(command->bearing).withPitch(command->pitch)); return;
        }
        if (command->command == "set_poi_focus") {
            const bool fuel = command->category == "fuel";
            setLayerVisible(map.getStyle(), "fuel-focus-glow", fuel);
            setLayerVisible(map.getStyle(), "fuel-focus-label", fuel);
            std::cout << "[map_renderer] POI focus: " << (fuel ? "fuel" : "off") << '\n'; return;
        }
        if (command->command == "set_route") {
            auto* source = map.getStyle().getSource("route"); if (!source) return;
            auto* routeSource = static_cast<mbgl::style::GeoJSONSource*>(source);
            try { routeSource->setGeoJSON(mapbox::geojson::parse(command->geojson)); }
            catch (const std::exception& exception) { std::cerr << "[map_renderer] failed to parse route GeoJSON: " << exception.what() << '\n'; }
            return;
        }
    });
    map.getStyle().loadJSON(styleJson);
    view.run(); return 0;
}
