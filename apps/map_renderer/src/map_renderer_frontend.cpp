// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT

#include "map_renderer_frontend.hpp"

#include "map_view.hpp"

#include <mbgl/gfx/backend_scope.hpp>
#include <mbgl/gfx/renderer_backend.hpp>
#include <mbgl/renderer/renderer.hpp>
#include <mbgl/util/instrumentation.hpp>

#include <cassert>
#include <iostream>

MapRendererFrontend::MapRendererFrontend(
    std::unique_ptr<mbgl::Renderer> renderer_,
    MapView& mapView_
)
    : mapView(mapView_),
      renderer(std::move(renderer_))
{
    mapView.setRendererFrontend(this);
}


MapRendererFrontend::~MapRendererFrontend() =
    default;


void MapRendererFrontend::reset()
{
    assert(renderer);
    renderer.reset();
}


void MapRendererFrontend::setObserver(
    mbgl::RendererObserver& observer
)
{
    assert(renderer);
    renderer->setObserver(&observer);
}


void MapRendererFrontend::update(
    std::shared_ptr<mbgl::UpdateParameters> params
)
{
    updateParameters =
        std::move(params);

    mapView.invalidate();
}


const mbgl::TaggedScheduler&
MapRendererFrontend::getThreadPool() const
{
    return mapView
        .getRendererBackend()
        .getThreadPool();
}


void MapRendererFrontend::render()
{
    MLN_TRACE_FUNC();

    assert(renderer);

    if (!updateParameters) {
        return;
    }

    mbgl::gfx::BackendScope guard{
        mapView.getRendererBackend(),
        mbgl::gfx::BackendScope::ScopeType::Implicit
    };

    auto updateParameters_ =
        updateParameters;

    renderer->render(
        updateParameters_
    );
}


mbgl::Renderer*
MapRendererFrontend::getRenderer()
{
    assert(renderer);
    return renderer.get();
}
