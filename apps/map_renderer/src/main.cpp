// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT
#include "map_renderer_frontend.hpp"
#include "map_view.hpp"
#include "map_command_server.hpp"
#include "map_event_publisher.hpp"
#include "navigation_config.hpp"
#include <mbgl/map/map.hpp>
#include <mbgl/renderer/renderer.hpp>
#include <mbgl/style/layer.hpp>
#include <mbgl/style/style.hpp>
#include <mbgl/style/sources/geojson_source.hpp>
#include <mapbox/geojson.hpp>
#include <sqlite3.h>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <iterator>
#include <memory>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>

namespace {
constexpr double kDefaultLatitude = 0.0;
constexpr double kDefaultLongitude = 0.0;
constexpr double kDefaultZoom = 2.0;
constexpr double kDatasetBoundsPadding = 24.0;
constexpr const char* kDefaultBrokerPublisherEndpoint = "tcp://127.0.0.1:5556";
constexpr const char* kDefaultBrokerSubscriberEndpoint = "tcp://127.0.0.1:5557";
constexpr const char* kDataRootToken = "__OPENROADCODE_DATA_ROOT__";
constexpr const char* kLegacyDataRoot = "/srv/openroadcode";

std::string environmentOrDefault(const char* name, const char* fallback) {
    const auto* value = std::getenv(name);
    return value && value[0] != '\0' ? value : fallback;
}

void replaceAll(std::string& value, const std::string& from, const std::string& to) {
    if (from.empty()) return;
    std::size_t offset = 0;
    while ((offset = value.find(from, offset)) != std::string::npos) {
        value.replace(offset, from.length(), to);
        offset += to.length();
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
    if (layer) layer->setVisibility(visible ? mbgl::style::VisibilityType::Visible : mbgl::style::VisibilityType::None);
}

std::optional<mbgl::LatLngBounds> loadDatasetBounds(const std::string& dataRoot) {
    const std::string path = dataRoot + "/maps/vector/openroadcode.mbtiles";
    sqlite3* database = nullptr;
    if (sqlite3_open_v2(path.c_str(), &database, SQLITE_OPEN_READONLY, nullptr) != SQLITE_OK) {
        std::cerr << "[map_renderer] unable to read MBTiles metadata: " << path << '\n';
        if (database) sqlite3_close(database);
        return std::nullopt;
    }

    sqlite3_stmt* statement = nullptr;
    const char* sql = "SELECT value FROM metadata WHERE name='bounds' LIMIT 1";
    if (sqlite3_prepare_v2(database, sql, -1, &statement, nullptr) != SQLITE_OK) {
        sqlite3_close(database);
        return std::nullopt;
    }

    std::optional<mbgl::LatLngBounds> result;
    if (sqlite3_step(statement) == SQLITE_ROW) {
        const auto* text = sqlite3_column_text(statement, 0);
        if (text) {
            std::istringstream input(reinterpret_cast<const char*>(text));
            double west = 0.0, south = 0.0, east = 0.0, north = 0.0;
            char comma1 = 0, comma2 = 0, comma3 = 0;
            if (input >> west >> comma1 >> south >> comma2 >> east >> comma3 >> north &&
                comma1 == ',' && comma2 == ',' && comma3 == ',' &&
                south >= -90.0 && north <= 90.0 && west >= -180.0 && east <= 180.0 &&
                south < north && west < east) {
                result = mbgl::LatLngBounds::hull(
                    mbgl::LatLng{south, west}, mbgl::LatLng{north, east});
                std::cout << "[map_renderer] dataset bounds: "
                          << west << ',' << south << ',' << east << ',' << north << '\n';
            }
        }
    }

    sqlite3_finalize(statement);
    sqlite3_close(database);
    return result;
}

bool fitDatasetCamera(mbgl::Map& map, const NavigationConfig& config, double padding, bool animated) {
    const auto bounds = loadDatasetBounds(config.dataRoot);
    if (!bounds) return false;
    const mbgl::EdgeInsets insets{padding, padding, padding, padding};
    const auto camera = map.cameraForLatLngBounds(*bounds, insets);
    if (animated) map.easeTo(camera, mbgl::AnimationOptions{mbgl::Milliseconds(500)});
    else map.jumpTo(camera);
    return true;
}

void setInitialCamera(mbgl::Map& map, const NavigationConfig& config) {
    if (fitDatasetCamera(map, config, kDatasetBoundsPadding, false)) return;
    std::cerr << "[map_renderer] MBTiles bounds unavailable; using generic fallback camera\n";
    map.jumpTo(mbgl::CameraOptions()
        .withCenter(mbgl::LatLng{kDefaultLatitude, kDefaultLongitude})
        .withZoom(kDefaultZoom));
}
}

int main() {
    const auto configPath = environmentOrDefault(
        "OPENROADCODE_NAVIGATION_CONFIG", "/etc/openroadcode/navigation.toml");
    const auto publisherEndpoint = environmentOrDefault(
        "OPENROADCODE_BROKER_PUBLISHER_ENDPOINT", kDefaultBrokerPublisherEndpoint);
    const auto subscriberEndpoint = environmentOrDefault(
        "OPENROADCODE_BROKER_SUBSCRIBER_ENDPOINT", kDefaultBrokerSubscriberEndpoint);

    NavigationConfig config;
    try {
        config = loadNavigationConfig(configPath);
    } catch (const std::exception& error) {
        std::cerr << "[map_renderer] invalid navigation config: " << error.what() << '\n';
        return 1;
    }

    std::string styleJson;
    try {
        styleJson = loadStyleJson(config);
    } catch (const std::exception& error) {
        std::cerr << "[map_renderer] failed to load navigation style: " << error.what() << '\n';
        return 1;
    }

    mbgl::ResourceOptions resourceOptions;
    resourceOptions.withCachePath(config.cachePath);
    mbgl::ClientOptions clientOptions;
    MapView view(resourceOptions, clientOptions);
    MapRendererFrontend rendererFrontend{
        std::make_unique<mbgl::Renderer>(view.getRendererBackend(), view.getPixelRatio()), view};
    mbgl::Map map(
        rendererFrontend,
        view,
        mbgl::MapOptions().withSize(view.getSize()).withPixelRatio(view.getPixelRatio()),
        resourceOptions,
        clientOptions);
    view.setMap(&map);
    setInitialCamera(map, config);

    MapCommandServer commandServer(subscriberEndpoint);
    MapEventPublisher eventPublisher(publisherEndpoint);
    view.setPoiSelectedCallback(
        [&eventPublisher](const std::string& name,
                          const std::string& brand,
                          const std::string& sourceClass,
                          const std::string& sourceSubclass,
                          double latitude,
                          double longitude) {
            eventPublisher.publishPoiSelected(
                name, brand, sourceClass, sourceSubclass, latitude, longitude);
        });

    view.setUpdateCallback([&map, &commandServer, &config, &view, &eventPublisher]() {
        // Drain the command socket every frame instead of processing only one
        // message. Position telemetry can be much faster than UI input; leaving
        // old messages queued made camera buttons appear frozen until a renderer
        // restart discarded the backlog.
        while (true) {
            const auto command = commandServer.poll();
            if (!command) break;

            if (command->command == "set_center") {
                map.jumpTo(mbgl::CameraOptions().withCenter(
                    mbgl::LatLng{command->latitude, command->longitude}));
                continue;
            }
            if (command->command == "fit_bounds") {
                const auto bounds = mbgl::LatLngBounds::hull(
                    mbgl::LatLng{command->south, command->west},
                    mbgl::LatLng{command->north, command->east});
                const mbgl::EdgeInsets padding{
                    command->padding, command->padding, command->padding, command->padding};
                map.easeTo(
                    map.cameraForLatLngBounds(bounds, padding),
                    mbgl::AnimationOptions{mbgl::Milliseconds(500)});
                continue;
            }
            if (command->command == "fit_dataset") {
                if (!fitDatasetCamera(map, config, command->padding, true)) {
                    std::cerr << "[map_renderer] unable to fit dataset bounds\n";
                }
                continue;
            }
            if (command->command == "set_position") {
                auto* source = map.getStyle().getSource("vehicle");
                if (!source) continue;
                auto* vehicleSource = static_cast<mbgl::style::GeoJSONSource*>(source);
                mapbox::geojson::feature feature{
                    mapbox::geojson::geometry{
                        mapbox::geometry::point<double>{command->longitude, command->latitude}}};
                feature.properties["marker_mode"] = config.markerMode;
                feature.properties["marker_scale"] = config.markerScale;
                vehicleSource->setGeoJSON(feature);
                continue;
            }
            if (command->command == "set_camera") {
                // UI camera commands are state changes, not cinematic transitions.
                // Jump immediately so repeated GPS/camera updates cannot pile up
                // overlapping 450 ms animations.
                map.jumpTo(mbgl::CameraOptions()
                    .withCenter(mbgl::LatLng{command->latitude, command->longitude})
                    .withZoom(command->zoom)
                    .withBearing(command->bearing)
                    .withPitch(command->pitch));
                continue;
            }
            if (command->command == "search_pois") {
                const auto result = view.searchVisiblePois(command->category);
                eventPublisher.publishPoiSearchResult(
                    command->category,
                    result.count,
                    result.south,
                    result.west,
                    result.north,
                    result.east);
                continue;
            }
            if (command->command == "set_poi_focus") {
                if (command->category == "fuel") {
                    setLayerVisible(map.getStyle(), "fuel-focus-glow", command->enabled);
                    setLayerVisible(map.getStyle(), "fuel-focus-label", command->enabled);
                } else if (command->category == "grocery") {
                    setLayerVisible(map.getStyle(), "grocery-focus-glow", command->enabled);
                    setLayerVisible(map.getStyle(), "grocery-focus-label", command->enabled);
                }
                view.invalidate();
                continue;
            }
            if (command->command == "set_route") {
                auto* source = map.getStyle().getSource("route");
                if (!source) continue;
                auto* routeSource = static_cast<mbgl::style::GeoJSONSource*>(source);
                try {
                    routeSource->setGeoJSON(mapbox::geojson::parse(command->geojson));
                } catch (const std::exception& error) {
                    std::cerr << "[map_renderer] failed to parse route GeoJSON: "
                              << error.what() << '\n';
                }
            }
        }
    });

    map.getStyle().loadJSON(styleJson);
    view.run();
    return 0;
}
