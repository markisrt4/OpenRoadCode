// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT
#include "map_renderer_frontend.hpp"
#include "map_view.hpp"
#include "map_command_server.hpp"
#include "map_event_publisher.hpp"
#include "navigation_config.hpp"
#include "route_weather_style.hpp"
#include "city_weather_style.hpp"
#include "poi_hover_style.hpp"
#include "orc_logging.hpp"
#include <mbgl/map/map.hpp>
#include <mbgl/renderer/renderer.hpp>
#include <mbgl/style/layer.hpp>
#include <mbgl/style/layers/raster_layer.hpp>
#include <mbgl/style/style.hpp>
#include <mbgl/style/sources/geojson_source.hpp>
#include <mbgl/style/sources/raster_source.hpp>
#include <mbgl/style/sources/tile_source.hpp>
#include <mapbox/geojson.hpp>
#include <sqlite3.h>
#include <cstdlib>
#include <array>
#include <chrono>
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
constexpr const char* kWeatherRadarSourceId = "weather-radar";
constexpr const char* kWeatherRadarLayerId = "weather-radar";
constexpr uint16_t kWeatherRadarTileSize = 256;

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
    return withCityWeatherStyle(withPoiHoverStyle(withRouteWeatherStyle(style)));
}
void setWeatherRaster(
    mbgl::style::Style& style,
    const MapCommand& command,
    std::string& currentTileUrl,
    const char* sourceId = kWeatherRadarSourceId,
    const char* layerId = kWeatherRadarLayerId,
    bool locatorRings = true
) {
    if (locatorRings) {
        for (const auto* id : {"radar-position-ring-inner", "radar-position-ring-middle",
                               "radar-position-ring-outer"}) {
            if (auto* ring = style.getLayer(id)) {
                ring->setVisibility(command.enabled ? mbgl::style::VisibilityType::Visible
                                                     : mbgl::style::VisibilityType::None);
            }
        }
    }
    auto* existingLayer = style.getLayer(layerId);
    if (!command.enabled) {
        if (existingLayer != nullptr) {
            existingLayer->setVisibility(mbgl::style::VisibilityType::None);
        }
        return;
    }

    if (command.tileUrl.empty() || (existingLayer != nullptr && command.tileUrl == currentTileUrl)) {
        if (existingLayer != nullptr) {
            auto* radarLayer = static_cast<mbgl::style::RasterLayer*>(existingLayer);
            radarLayer->setRasterOpacity(command.opacity);
            radarLayer->setVisibility(mbgl::style::VisibilityType::Visible);
        }
        return;
    }

    // A supplied URL selects a new frame. Recreate only for frame changes;
    // visibility-only commands preserve the existing source and tile cache.
    if (existingLayer != nullptr) {
        style.removeLayer(layerId);
    }
    if (style.getSource(sourceId) != nullptr) {
        style.removeSource(sourceId);
    }

    mbgl::Tileset tileset;
    tileset.tiles = {command.tileUrl};
    tileset.zoomRange = {0, static_cast<uint8_t>(command.maxZoom)};
    auto source = std::make_unique<mbgl::style::RasterSource>(
        sourceId,
        std::move(tileset),
        kWeatherRadarTileSize
    );
    style.addSource(std::move(source));
    currentTileUrl = command.tileUrl;

    auto layer = std::make_unique<mbgl::style::RasterLayer>(
        layerId,
        sourceId
    );
    layer->setRasterOpacity(command.opacity);

    // Keep navigation overlays readable. The route source is part of the
    // canonical ORC style, so placing radar immediately below its first layer
    // leaves route/vehicle rendering above precipitation.
    const std::string anchor = !locatorRings && style.getLayer(kWeatherRadarLayerId)
        ? kWeatherRadarLayerId : "route-line-casing";
    style.addLayer(std::move(layer), style.getLayer(anchor)
        ? std::optional<std::string>{anchor} : std::nullopt);
}

void setLayerVisible(mbgl::style::Style& style, const char* id, bool visible) {
    auto* layer = style.getLayer(id);
    const auto visibility = visible ? mbgl::style::VisibilityType::Visible : mbgl::style::VisibilityType::None;
    if (layer && layer->getVisibility() != visibility) layer->setVisibility(visibility);
}

std::optional<mbgl::LatLngBounds> loadDatasetBounds(const std::string& dataRoot) {
    const std::string path = dataRoot + "/maps/vector/openroadcode.mbtiles";
    sqlite3* database = nullptr;
    if (sqlite3_open_v2(path.c_str(), &database, SQLITE_OPEN_READONLY, nullptr) != SQLITE_OK) {
        orc::log("WARNING", "map_renderer.dataset", "dataset.metadata_unavailable", "Unable to read MBTiles metadata");
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
                orc::log("DEBUG", "map_renderer.dataset", "dataset.bounds_loaded", "Dataset bounds loaded");
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
    orc::log("WARNING", "map_renderer.dataset", "dataset.bounds_unavailable", "Using fallback map camera");
    map.jumpTo(mbgl::CameraOptions()
        .withCenter(mbgl::LatLng{kDefaultLatitude, kDefaultLongitude})
        .withZoom(kDefaultZoom));
}
}

int runRenderer() {
    orc::log("INFO", "map_renderer.lifecycle", "process.started", "Map renderer starting");
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
        orc::log("CRITICAL", "map_renderer.lifecycle", "config.invalid", "Invalid navigation configuration");
        return 1;
    }

    std::string styleJson;
    try {
        styleJson = loadStyleJson(config);
    } catch (const std::exception& error) {
        orc::log("CRITICAL", "map_renderer.lifecycle", "style.failed", "Failed to load navigation style");
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

    std::string currentRadarTileUrl;
    std::string currentWeatherFieldUrl;
    MapCommandServer commandServer(subscriberEndpoint);
    MapEventPublisher eventPublisher(publisherEndpoint);
    view.setManualCameraCallback(
        [&eventPublisher]() {
            eventPublisher.publishManualCameraInteraction();
        });

    view.setMapClickCallback(
        [&eventPublisher](
            double latitude,
            double longitude,
            double selectionRadiusM,
            const std::string& markerId,
            std::size_t markerIndex) {
            eventPublisher.publishMapClick(
                latitude, longitude, selectionRadiusM, markerId, markerIndex);
        });

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

    bool cameraOwnedByUi = false;
    std::optional<std::array<double, 5>> lastCamera;
    auto lastCameraReport = std::chrono::steady_clock::time_point{};
    view.setUpdateCallback([&]() {
        // Drain the command socket every frame instead of processing only one
        // message. Position telemetry can be much faster than UI input; leaving
        // old messages queued made camera buttons appear frozen until a renderer
        // restart discarded the backlog.
        while (true) {
            const auto command = commandServer.poll();
            if (!command) break;

            // A toolbar camera command ends direct manipulation. Telemetry and
            // POI updates must not interrupt an active mouse gesture.
            if (command->command == "set_center" || command->command == "set_camera" ||
                command->command == "fit_bounds" || command->command == "fit_dataset" ||
                command->command == "set_zoom" || command->command == "set_bearing" ||
                command->command == "set_pitch" || command->command == "pan_screen") {
                view.finishCameraGesture();
                cameraOwnedByUi = true;
            }

            if (command->command == "set_center") {
                map.jumpTo(mbgl::CameraOptions().withCenter(
                    mbgl::LatLng{command->latitude, command->longitude}));
                view.showWindow();
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
                view.showWindow();
                continue;
            }
            if (command->command == "fit_dataset") {
                if (!fitDatasetCamera(map, config, command->padding, true)) {
                    orc::log("WARNING", "map_renderer.dataset", "dataset.fit_failed", "Unable to fit dataset bounds");
                }
                view.showWindow();
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
                // Embedded renderers start hidden. Reveal only after the owning
                // panel has supplied its semantic camera so users never see the
                // temporary dataset camera during HOME/NAV renderer replacement.
                view.showWindow();
                continue;
            }
            if (command->command == "set_zoom") {
                map.jumpTo(mbgl::CameraOptions().withZoom(command->zoom));
                continue;
            }
            if (command->command == "set_bearing") {
                map.jumpTo(mbgl::CameraOptions().withBearing(command->bearing));
                continue;
            }
            if (command->command == "set_pitch") {
                map.jumpTo(mbgl::CameraOptions().withPitch(command->pitch));
                continue;
            }
            if (command->command == "pan_screen") {
                // moveBy() translates the rendered map, which is the inverse of
                // the semantic direction requested by the UI pan controls.
                map.moveBy({-command->rightPx, command->upPx});
                continue;
            }
            if (command->command == "search_weather_cities") {
                eventPublisher.publishWeatherCities(command->requestId, view.searchWeatherCities());
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
            if (command->command == "set_poi_results") {
                auto* source = map.getStyle().getSource("poi-results");
                if (!source) continue;
                auto* poiSource = static_cast<mbgl::style::GeoJSONSource*>(source);
                try {
                    poiSource->setGeoJSON(mapbox::geojson::parse(command->geojson));
                    view.setPoiResultsJson(command->geojson);
                    view.invalidate();
                } catch (const std::exception& error) {
                    orc::log("ERROR", "map_renderer.pois", "pois.failed", "Failed to apply POI GeoJSON");
                }
                continue;
            }
            if (command->command == "set_poi_focus") {
                if (command->category == "fuel") {
                    setLayerVisible(map.getStyle(), "fuel-focus-glow", command->enabled);
                    setLayerVisible(map.getStyle(), "fuel-focus-label", command->enabled);
                } else if (command->category == "grocery") {
                    setLayerVisible(map.getStyle(), "grocery-focus-glow", command->enabled);
                    setLayerVisible(map.getStyle(), "grocery-focus-label", command->enabled);
                } else if (command->category == "food") {
                    setLayerVisible(map.getStyle(), "food-focus-glow", command->enabled);
                    setLayerVisible(map.getStyle(), "food-focus-label", command->enabled);
                } else if (command->category == "transit") {
                    setLayerVisible(map.getStyle(), "transit-focus-glow", command->enabled);
                    setLayerVisible(map.getStyle(), "transit-focus-label", command->enabled);
                }
                view.invalidate();
                continue;
            }
            if (command->command == "set_weather_field") {
                setWeatherRaster(map.getStyle(), *command, currentWeatherFieldUrl,
                                 "weather-field", "weather-field", false);
                view.invalidate();
                continue;
            }
            if (command->command == "set_weather_radar") {
                try {
                    setWeatherRaster(map.getStyle(), *command, currentRadarTileUrl);
                    view.invalidate();
                    std::cout << "[map_renderer] weather radar: "
                              << (command->enabled ? "on" : "off")
                              << " opacity=" << command->opacity
                              << " frame=" << command->frameTime << '\n';
                } catch (const std::exception& exception) {
                    std::cerr << "[map_renderer] failed to update weather radar: "
                              << exception.what() << '\n';
                }
                continue;
            }
            if (command->command == "set_route_weather" || command->command == "set_city_weather") {
                auto* source = map.getStyle().getSource(
                    command->command == "set_city_weather" ? "city-weather" : "route-weather");
                if (!source) continue;
                try {
                    static_cast<mbgl::style::GeoJSONSource*>(source)->setGeoJSON(
                        mapbox::geojson::parse(command->geojson));
                    if (command->command == "set_city_weather")
                        view.setCityWeatherJson(command->geojson);
                    view.invalidate();
                } catch (const std::exception& error) {
                    std::cerr << "[map_renderer] invalid weather labels: " << error.what() << '\n';
                }
                continue;
            }
            if (command->command == "set_route") {
                auto* source = map.getStyle().getSource("route");
                if (!source) {
                    orc::log("ERROR", "map_renderer.routes", "route.source_missing", "Map style has no route source", command->operationId);
                    continue;
                }
                auto* routeSource = static_cast<mbgl::style::GeoJSONSource*>(source);
                try {
                    routeSource->setGeoJSON(mapbox::geojson::parse(command->geojson));
                    orc::log("INFO", "map_renderer.routes", "route.applied", "Route applied", command->operationId);
                } catch (const std::exception& error) {
                    orc::log("ERROR", "map_renderer.routes", "route.failed", "Failed to apply route GeoJSON", command->operationId);
                }
            }
        }
        // Match building geometry to the actual camera, including gesture and
        // follow updates. Flat mode must not keep extruded roofs underneath.
        const bool tilted = map.getCameraOptions().pitch.value_or(0.0) > 0.01;
        setLayerVisible(map.getStyle(), "buildings", tilted);
        setLayerVisible(map.getStyle(), "buildings-flat", !tilted);
        setLayerVisible(map.getStyle(), "house-numbers", !tilted);
        const auto camera = map.getCameraOptions();
        const auto now = std::chrono::steady_clock::now();
        if (cameraOwnedByUi && camera.center && camera.zoom && camera.bearing && camera.pitch &&
            now - lastCameraReport >= std::chrono::milliseconds(50)) {
            const std::array<double, 5> snapshot{
                camera.center->latitude(), camera.center->longitude(),
                *camera.zoom, *camera.bearing, *camera.pitch};
            if (!lastCamera || *lastCamera != snapshot) {
                eventPublisher.publishCameraState(snapshot[0], snapshot[1], snapshot[2], snapshot[3], snapshot[4]);
                lastCamera = snapshot;
                lastCameraReport = now;
            }
        }
    });

    map.getStyle().loadJSON(styleJson);
    view.run();
    orc::log("INFO", "map_renderer.lifecycle", "process.stopped", "Map renderer stopped");
    return 0;
}


int main() {
    try {
        return runRenderer();
    } catch (const std::exception&) {
        orc::log("CRITICAL", "map_renderer.lifecycle", "process.failed", "Map renderer failed");
        return 1;
    }
}
