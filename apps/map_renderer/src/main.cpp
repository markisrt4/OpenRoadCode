// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT

#include "map_renderer_frontend.hpp"
#include "map_view.hpp"
#include "map_command_server.hpp"

#include <mbgl/map/map.hpp>
#include <mbgl/renderer/renderer.hpp>
#include <mbgl/style/style.hpp>
#include <mbgl/style/sources/geojson_source.hpp>
#include <mapbox/geojson.hpp>

#include <memory>
#include <string>
#include <iostream>

namespace {

constexpr double kLatitude =
    42.3314;

constexpr double kLongitude =
    -83.0458;

constexpr double kZoom =
    13.0;

constexpr const char* kStyleUrl =
    "file:///srv/openroadcode/maps/styles/"
    "michigan-test.json";

constexpr const char* kCachePath =
    "/tmp/openroadcode-map-cache.db";

}


int main()
{
    mbgl::ResourceOptions resourceOptions;

    resourceOptions.withCachePath(
        kCachePath
    );

    mbgl::ClientOptions clientOptions;

    MapView view(
        resourceOptions,
        clientOptions
    );

    MapRendererFrontend rendererFrontend{
        std::make_unique<
            mbgl::Renderer
        >(
            view.getRendererBackend(),
            view.getPixelRatio()
        ),
        view
    };

    mbgl::Map map(
        rendererFrontend,
        view,
        mbgl::MapOptions()
            .withSize(
                view.getSize()
            )
            .withPixelRatio(
                view.getPixelRatio()
            ),
        resourceOptions,
        clientOptions
    );

    view.setMap(
        &map
    );

    map.jumpTo(
        mbgl::CameraOptions()
            .withCenter(
                mbgl::LatLng{
                    kLatitude,
                    kLongitude
                }
            )
            .withZoom(
                kZoom
            )
    );

    MapCommandServer commandServer;

    view.setUpdateCallback(
        [&map, &commandServer, &view]() {
            const auto command =
                commandServer.poll();

            if (!command) {
                return;
            }

            if (command->command == "set_center")
            {
                std::cout
                    << "[map_renderer] set_center: "
                    << command->latitude  << ", "
                    << command->longitude << '\n';

                map.jumpTo(mbgl::CameraOptions().withCenter(mbgl::LatLng{
                                command->latitude,
                                command->longitude }
                        )
                );

                return;
            }

            if (command->command == "fit_bounds") {
                const mbgl::LatLngBounds bounds = mbgl::LatLngBounds::hull(mbgl::LatLng{
                            command->south,
                            command->west
                        },
                        mbgl::LatLng{
                            command->north,
                            command->east
                        }
                    );

                const mbgl::EdgeInsets padding{
                    command->padding,
                    command->padding,
                    command->padding,
                    command->padding
                };

                const auto camera = map.cameraForLatLngBounds(bounds, padding);

                std::cout
                    << "[map_renderer] fit_bounds: "
                    << command->south << ", "
                    << command->west << " -> "
                    << command->north << ", "
                    << command->east
                    << '\n';

                map.easeTo(
                    camera,
                    mbgl::AnimationOptions{
                        mbgl::Milliseconds(500)
                    }
                );

                return;
            }

            if (command->command == "set_position")
            {
                auto* source = map.getStyle().getSource("vehicle");

                if (!source)
                {
                    std::cerr << "[map_renderer] vehicle source not found\n";
                    return;
                }

                auto* vehicleSource = static_cast<mbgl::style::GeoJSONSource*>(source);

                const mapbox::geojson::geometry geometry = mapbox::geometry::point<double>{
                        command->longitude,
                        command->latitude
                    };

                vehicleSource->setGeoJSON(geometry);
                //view.invalidate();

                return;
            }

            if (command->command == "set_camera")
            {
                map.jumpTo(mbgl::CameraOptions().withCenter(mbgl::LatLng{
                                command->latitude,
                                command->longitude}
                        )
                        .withZoom   (command->zoom)
                        .withBearing(command->bearing)
                        .withPitch  (command->pitch)
                );
            }

            if (command->command == "set_route")
            {
                auto* source = map.getStyle().getSource("route");

                if (!source)
                {
                    std::cerr << "[map_renderer] route source not found\n";
                    return;
                }

                auto* routeSource = static_cast<mbgl::style::GeoJSONSource*>(source);

                if (!routeSource)
                {
                    std::cerr << "[map_renderer] route source not found\n";

                    return;
                }

                try
                {
                    const auto geojson = mapbox::geojson::parse(command->geojson);

                    routeSource->setGeoJSON(geojson);

                    std::cout << "[map_renderer] route updated\n";
                }
                catch
                (
                    const std::exception& exception
                )
                {
                    std::cerr
                        << "[map_renderer] failed to parse route GeoJSON: "
                        << exception.what()
                        << '\n';
                }

                return;
            }
        }
    );

    map.getStyle().loadURL(kStyleUrl);

    view.run();

    return 0;
}
