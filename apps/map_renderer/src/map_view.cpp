// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT

#include "map_view.hpp"

#include "map_renderer_frontend.hpp"

#include "glfw_backend.hpp"

#include <mbgl/gfx/backend.hpp>
#include <mbgl/gfx/backend_scope.hpp>
#include <mbgl/util/logging.hpp>

#define GLFW_INCLUDE_ES3
#define GL_GLEXT_PROTOTYPES
#include <GLFW/glfw3.h>

#include <cmath>
#include <cstdlib>
#include <iostream>


namespace {

void glfwError(
    int error,
    const char* description
)
{
    mbgl::Log::Error(
        mbgl::Event::OpenGL,
        std::string("GLFW error (") +
            std::to_string(error) +
            "): " +
            description
    );
}

}


MapView::MapView(
    const mbgl::ResourceOptions&,
    const mbgl::ClientOptions&
)
{
    glfwSetErrorCallback(glfwError);

    if (!glfwInit()) {
        mbgl::Log::Error(
            mbgl::Event::OpenGL,
            "Failed to initialize GLFW"
        );

        std::exit(1);
    }

    /*
     * Match the known-good MapLibre OpenGL configuration.
     */
    if (
        mbgl::gfx::Backend::GetType() ==
        mbgl::gfx::Backend::Type::OpenGL
    ) {
#if MBGL_WITH_EGL
        glfwWindowHint(
            GLFW_CONTEXT_CREATION_API,
            GLFW_EGL_CONTEXT_API
        );
#endif

        glfwWindowHint(
            GLFW_CLIENT_API,
            GLFW_OPENGL_ES_API
        );

        glfwWindowHint(
            GLFW_CONTEXT_VERSION_MAJOR,
            3
        );

        glfwWindowHint(
            GLFW_CONTEXT_VERSION_MINOR,
            0
        );

        glfwWindowHint(GLFW_RED_BITS, 8);
        glfwWindowHint(GLFW_GREEN_BITS, 8);
        glfwWindowHint(GLFW_BLUE_BITS, 8);
        glfwWindowHint(GLFW_ALPHA_BITS, 8);
        glfwWindowHint(GLFW_STENCIL_BITS, 8);
        glfwWindowHint(GLFW_DEPTH_BITS, 16);
    } else {
        glfwWindowHint(
            GLFW_CLIENT_API,
            GLFW_NO_API
        );
    }

    window = glfwCreateWindow(
        width,
        height,
        "OpenRoadCode Map Renderer",
        nullptr,
        nullptr
    );

    if (!window) {
        glfwTerminate();

        mbgl::Log::Error(
            mbgl::Event::OpenGL,
            "Failed to create GLFW window"
        );

        std::exit(1);
    }

    glfwSetWindowUserPointer(
        window,
        this
    );

    glfwSetWindowSizeCallback(
        window,
        onWindowResize
    );

    glfwSetFramebufferSizeCallback(
        window,
        onFramebufferResize
    );

    glfwSetCursorPosCallback(
        window,
        onMouseMove
    );

    glfwSetMouseButtonCallback(
        window,
        onMouseClick
    );

    glfwSetScrollCallback(
        window,
        onScroll
    );

    /*
     * Important:
     *
     * Do NOT call glfwSwapInterval() here.
     *
     * The MapLibre GLFW OpenGL backend makes the context current
     * before configuring the swap interval. This is the bug we
     * encountered in the upstream GLFW example.
     */
    backend = GLFWBackend::Create(
        window,
        true
    );

    glfwGetWindowSize(
        window,
        &width,
        &height
    );

    pixelRatio =
        static_cast<float>(
            backend->getSize().width
        ) /
        static_cast<float>(width);

    /*
     * MapLibre manages the context when rendering.
     */
    glfwMakeContextCurrent(nullptr);
}


MapView::~MapView()
{
    if (window) {
        glfwDestroyWindow(window);
        window = nullptr;
    }

    glfwTerminate();
}


float MapView::getPixelRatio() const
{
    return pixelRatio;
}


mbgl::Size MapView::getSize() const
{
    return {
        static_cast<uint32_t>(width),
        static_cast<uint32_t>(height)
    };
}


mbgl::gfx::RendererBackend&
MapView::getRendererBackend()
{
    return backend->getRendererBackend();
}


void MapView::setMap(
    mbgl::Map* map_
)
{
    map = map_;
}


void MapView::setRendererFrontend(
    MapRendererFrontend* rendererFrontend_
)
{
    rendererFrontend = rendererFrontend_;
}


void MapView::setShouldClose()
{
    glfwSetWindowShouldClose(
        window,
        GLFW_TRUE
    );

    glfwPostEmptyEvent();
}


void MapView::onWindowResize(
    GLFWwindow* window,
    int width,
    int height
)
{
    auto* view =
        static_cast<MapView*>(
            glfwGetWindowUserPointer(window)
        );

    if (!view) {
        return;
    }

    view->width = width;
    view->height = height;

    if (view->map) {
        view->map->setSize(
            {
                static_cast<uint32_t>(width),
                static_cast<uint32_t>(height)
            }
        );
    }
}


void MapView::onFramebufferResize(
    GLFWwindow* window,
    int width,
    int height
)
{
    auto* view =
        static_cast<MapView*>(
            glfwGetWindowUserPointer(window)
        );

    if (!view) {
        return;
    }

    view->backend->setSize(
        {
            static_cast<uint32_t>(width),
            static_cast<uint32_t>(height)
        }
    );

    view->invalidate();
}


void MapView::onScroll(
    GLFWwindow* window,
    double,
    double yOffset
)
{
    auto* view =
        static_cast<MapView*>(
            glfwGetWindowUserPointer(window)
        );

    if (!view || !view->map) {
        return;
    }

    const double delta =
        yOffset * 40.0;

    const double absDelta =
        std::abs(delta);

    double scale =
        2.0 /
        (
            1.0 +
            std::exp(
                -absDelta / 100.0
            )
        );

    if (delta < 0.0) {
        scale = 1.0 / scale;
    }

    view->map->scaleBy(
        scale,
        mbgl::ScreenCoordinate{
            view->lastX,
            view->lastY
        }
    );
}


void MapView::onMouseClick(
    GLFWwindow* window,
    int button,
    int action,
    int modifiers
)
{
    auto* view =
        static_cast<MapView*>(
            glfwGetWindowUserPointer(window)
        );

    if (!view || !view->map) {
        return;
    }

    if (
        button != GLFW_MOUSE_BUTTON_LEFT
    ) {
        return;
    }

    view->tracking =
        action == GLFW_PRESS;

    view->map->setGestureInProgress(
        view->tracking
    );

    if (action == GLFW_RELEASE) {
        const double now =
            glfwGetTime();

        /*
         * Keep the useful double-tap/double-click zoom behavior
         * from the MapLibre sample.
         */
        if (
            now - view->lastClick <
            0.4
        ) {
            const double scale =
                modifiers & GLFW_MOD_SHIFT
                    ? 0.5
                    : 2.0;

            view->map->scaleBy(
                scale,
                mbgl::ScreenCoordinate{
                    view->lastX,
                    view->lastY
                },
                mbgl::AnimationOptions{
                    {
                        mbgl::Milliseconds(
                            500
                        )
                    }
                }
            );
        }

        view->lastClick = now;
    }
}


void MapView::onMouseMove(
    GLFWwindow* window,
    double x,
    double y
)
{
    auto* view =
        static_cast<MapView*>(
            glfwGetWindowUserPointer(window)
        );

    if (!view || !view->map) {
        return;
    }

    if (view->tracking) {
        const double dx =
            x - view->lastX;

        const double dy =
            y - view->lastY;

        if (
            dx != 0.0 ||
            dy != 0.0
        ) {
            view->map->moveBy(
                mbgl::ScreenCoordinate{
                    dx,
                    dy
                }
            );
        }
    }

    view->lastX = x;
    view->lastY = y;
}


void MapView::render()
{
    static bool reportedNoRender = false;

    if (!dirty) {
        return;
    }

    if (!rendererFrontend) {
        if (!reportedNoRender) {
            std::cerr
                << "[map_renderer] dirty but rendererFrontend is null\n";
            reportedNoRender = true;
        }

        return;
    }

    dirty = false;

    mbgl::gfx::BackendScope scope{
        backend->getRendererBackend()
    };

    rendererFrontend->render();
}


void MapView::run()
{
    std::cout << "[map_renderer] entering GLFW event loop\n";

    auto callback = [&]() {
        if (
            glfwWindowShouldClose(
                window
            )
        ) {
            std::cout << "[map_renderer] GLFW requested window close\n";
            runLoop.stop();
            return;
        }

        glfwPollEvents();

        if (updateCallback) {
            updateCallback();
        }

        render();

#ifndef __APPLE__
        runLoop.updateTime();
#endif
    };

    /*
     * Match the normal MapLibre GLFW example:
     * 60 Hz application tick.
     */
    frameTick.start(
        mbgl::Duration::zero(),
        mbgl::Milliseconds(
            1000 / 60
        ),
        callback
    );

#if defined(__APPLE__)
    while (
        !glfwWindowShouldClose(window)
    ) {
        runLoop.run();
    }
#else
    runLoop.run();
#endif

    std::cout << "[map_renderer] GLFW event loop returned; windowShouldClose="
              << glfwWindowShouldClose(window) << '\n';
}


void MapView::invalidate()
{
    dirty = true;

    glfwPostEmptyEvent();
}


void MapView::onWillStartRenderingFrame()
{
    invalidate();
}

void MapView::setUpdateCallback(std::function<void()> callback)
{
    updateCallback = std::move(callback);
}
