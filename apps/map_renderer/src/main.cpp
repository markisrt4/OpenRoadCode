#include "map_renderer_frontend.hpp"
#include "map_view.hpp"
#include "map_command_server.hpp"

#include <mbgl/map/map.hpp>
#include <mbgl/renderer/renderer.hpp>
#include <mbgl/style/style.hpp>

#include <memory>
#include <string>
#include <iostream>

namespace {

constexpr double kLatitude =
    42.8028;

constexpr double kLongitude =
    -83.0127;

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
        [&map, &commandServer]() {
            const auto command = commandServer.poll();

            if (!command) {
                return;
            }

            std::cout
                << "[map_renderer] set_center: "
                << command->latitude
                << ", "
                << command->longitude
                << '\n';

            map.jumpTo(
                mbgl::CameraOptions()
                    .withCenter(
                        mbgl::LatLng{
                            command->latitude,
                            command->longitude
                        }
                    )
            );
        }
    );

    map.getStyle().loadURL(
        kStyleUrl
    );

    view.run();

    return 0;
}
