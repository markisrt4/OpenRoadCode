#pragma once

#include <mbgl/map/map.hpp>
#include <mbgl/renderer/renderer_frontend.hpp>

#include <memory>

namespace mbgl {

class Renderer;
class RendererObserver;
class UpdateParameters;

}

class MapView;

class MapRendererFrontend
    : public mbgl::RendererFrontend
{
public:
    MapRendererFrontend(
        std::unique_ptr<mbgl::Renderer> renderer,
        MapView& mapView
    );

    ~MapRendererFrontend() override;

    void reset() override;

    void setObserver(
        mbgl::RendererObserver& observer
    ) override;

    void update(
        std::shared_ptr<
            mbgl::UpdateParameters
        > updateParameters
    ) override;

    const mbgl::TaggedScheduler&
    getThreadPool() const override;

    void render();

    mbgl::Renderer* getRenderer();

private:
    MapView& mapView;

    std::unique_ptr<
        mbgl::Renderer
    > renderer;

    std::shared_ptr<
        mbgl::UpdateParameters
    > updateParameters;
};
