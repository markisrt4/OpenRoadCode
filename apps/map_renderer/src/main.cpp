// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT

#include "map_renderer_frontend.hpp"
#include "map_view.hpp"
#include "map_command_server.hpp"
#include "navigation_config.hpp"

#include <mbgl/map/map.hpp>
#include <mbgl/renderer/renderer.hpp>
#include <mbgl/style/style.hpp>
#include <mbgl/style/sources/geojson_source.hpp>
#include <mapbox/geojson.hpp>

#include <cstdlib>
#include <iostream>
#include <memory>
#include <string>

namespace {

constexpr double kLatitude = 42.3314;
constexpr double kLongitude = -83.0458;
constexpr double kZoom = 13.0;
constexpr const char* kDefaultRendererEndpoint = "ipc:///tmp/openroadcode-map-renderer";

std::string fileUrl(const std::string& path)
{
    if (path.rfind("file://", 0) == 0) {
        return path;
    }
    return "file://" + path;
}

std::string environmentOrDefault(const char* name, const char* fallback)
{
    const auto* configured = std::getenv(name);
    if (configured != nullptr && configured[0] != '\0') {
        return configured;
    }
    return fallback;
}

} // namespace

int main()
{
    const auto configPath = environmentOrDefault(
        "OPENROADCODE_NAVIGATION_CONFIG",
        "/etc/openroadcode/navigation.toml"
    );
    const auto rendererEndpoint = environmentOrDefault(
        "OPENROADCODE_MAP_RENDERER_ENDPOINT",
        kDefaultRendererEndpoint
    );

    NavigationConfig config;
    try {
        config = loadNavigationConfig(configPath);
    } catch (const std::exception& exception) {
        std::cerr << "[map_renderer] invalid navigation config: "
                  << exception.what() << '\n';
        return 1;
    }

    std::cout << "[map_renderer] config: " << configPath << '\n'
              << "[map_renderer] style: " << config.stylePath << '\n'
              << "[map_renderer] endpoint: " << rendererEndpoint << '\n'
              << "[map_renderer] vehicle marker: " << config.markerMode
              << " scale=" << config.markerScale << '\n';

    mbgl::ResourceOptions resourceOptions;
    resourceOptions.withCachePath(config.cachePath);

    mbgl::ClientOptions clientOptions;
    MapView view(resourceOptions, clientOptions);

    MapRendererFrontend rendererFrontend{
        std::make_unique<mbgl::Renderer>(
            view.getRendererBackend(),
            view.getPixelRatio()
        ),
        view
    };

    mbgl::Map map(
        rendererFrontend,
        view,
        mbgl::MapOptions()
            .withSize(view.getSize())
            .withPixelRatio(view.getPixelRatio()),
        resourceOptions,
        clientOptions
    );

    view.setMap(&map);
    map.jumpTo(
        mbgl::CameraOptions()
            .withCenter(mbgl::LatLng{kLatitude, kLongitude})
            .withZoom(kZoom)
    );

    MapCommandServer commandServer(rendererEndpoint);

    view.setUpdateCallback(
        [&map, &commandServer, &config]() {
            const auto command = commandServer.poll();
            if (!command) {
                return;
            }

            if (command->command == "set_center") {
                std::cout << "[map_renderer] set_center: "
                          << command->latitude << ", "
                          << command->longitude << '\n';
                map.jumpTo(
                    mbgl::CameraOptions().withCenter(
                        mbgl::LatLng{command->latitude, command->longitude}
                    )
                );
                return;
            }

            if (command->command == "fit_bounds") {
                const mbgl::LatLngBounds bounds = mbgl::LatLngBounds::hull(
                    mbgl::LatLng{command->south, command->west},
                    mbgl::LatLng{command->north, command->east}
                );
                const mbgl::EdgeInsets padding{
                    command->padding,
                    command->padding,
                    command->padding,
                    command->padding
                };
                const auto camera = map.cameraForLatLngBounds(bounds, padding);
                map.easeTo(camera, mbgl::AnimationOptions{mbgl::Milliseconds(500)});
                return;
            }

            if (command->command == "set_position") {
                auto* source = map.getStyle().getSource("vehicle");
                if (!source) {
                    std::cerr << "[map_renderer] vehicle source not found\n";
                    return;
                }

                auto* vehicleSource = static_cast<mbgl::style::GeoJSONSource*>(source);
                mapbox::geojson::feature feature{
                    mapbox::geojson::geometry{
                        mapbox::geometry::point<double>{
                            command->longitude,
                            command->latitude
                        }
                    }
                };
                feature.properties["marker_mode"] = config.markerMode;
                feature.properties["marker_scale"] = config.markerScale;
                vehicleSource->setGeoJSON(feature);
                return;
            }

            if (command->command == "set_camera") {
                map.jumpTo(
                    mbgl::CameraOptions()
                        .withCenter(mbgl::LatLng{
                            command->latitude,
                            command->longitude
                        })
                        .withZoom(command->zoom)
                        .withBearing(command->bearing)
                        .withPitch(command->pitch)
                );
                return;
            }

            if (command->command == "set_route") {
                auto* source = map.getStyle().getSource("route");
                if (!source) {
                    std::cerr << "[map_renderer] route source not found\n";
                    return;
                }

                auto* routeSource = static_cast<mbgl::style::GeoJSONSource*>(source);
                try {
                    const auto geojson = mapbox::geojson::parse(command->geojson);
                    routeSource->setGeoJSON(geojson);
                    std::cout << "[map_renderer] route updated\n";
                } catch (const std::exception& exception) {
                    std::cerr << "[map_renderer] failed to parse route GeoJSON: "
                              << exception.what() << '\n';
                }
                return;
            }
        }
    );

    map.getStyle().loadURL(fileUrl(config.stylePath));
    view.run();
    return 0;
}
