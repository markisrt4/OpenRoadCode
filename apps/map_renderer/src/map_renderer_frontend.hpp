// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT

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

/**
 * @brief Connects MapLibre rendering updates to a MapView window.
 *
 * MapLibre submits immutable update parameters through update(); the view is
 * invalidated and render() consumes the latest update in the GLFW event loop.
 */
class MapRendererFrontend
    : public mbgl::RendererFrontend
{
public:
    /**
     * @brief Construct a frontend that owns a MapLibre renderer.
     * @param renderer Renderer used to draw MapLibre frames.
     * @param mapView Window and backend that receive rendered frames.
     */
    MapRendererFrontend(
        std::unique_ptr<mbgl::Renderer> renderer,
        MapView& mapView
    );

    /** @brief Destroy the frontend and its renderer. */
    ~MapRendererFrontend() override;

    /** @brief Release the owned renderer. */
    void reset() override;

    /** @brief Install the observer that receives renderer events. */
    void setObserver(
        mbgl::RendererObserver& observer
    ) override;

    /** @brief Store a MapLibre update and schedule a frame. */
    void update(
        std::shared_ptr<
            mbgl::UpdateParameters
        > updateParameters
    ) override;

    /** @brief Return the scheduler owned by the view's renderer backend. */
    const mbgl::TaggedScheduler&
    getThreadPool() const override;

    /** @brief Render the most recently submitted update, when one exists. */
    void render();

    /** @brief Return the owned renderer, or `nullptr` after reset(). */
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
