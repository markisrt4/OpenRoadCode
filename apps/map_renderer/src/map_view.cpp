// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT

#include "map_view.hpp"

#include "map_renderer_frontend.hpp"
#include "glfw_backend.hpp"

#include <mbgl/gfx/backend.hpp>
#include <mbgl/gfx/backend_scope.hpp>
#include <mbgl/util/logging.hpp>

#define GLFW_INCLUDE_ES3
#define GLFW_EXPOSE_NATIVE_X11
#define GL_GLEXT_PROTOTYPES
#include <GLFW/glfw3.h>
#if defined(__linux__)
#include <GLFW/glfw3native.h>
#include <X11/Xlib.h>
#endif

#include <cmath>
#include <cstdlib>
#include <iostream>
#include <string>

namespace {

void glfwError(int error, const char* description)
{
    mbgl::Log::Error(
        mbgl::Event::OpenGL,
        std::string("GLFW error (") + std::to_string(error) + "): " + description
    );
}

#if defined(__linux__)
void embedInX11Parent(GLFWwindow* window)
{
    const char* parentValue = std::getenv("OPENROADCODE_MAP_PARENT_WINDOW");
    if (!parentValue || !*parentValue) {
        return;
    }

    char* end = nullptr;
    const unsigned long parentId = std::strtoul(parentValue, &end, 0);
    if (end == parentValue || *end != '\0' || parentId == 0) {
        std::cerr << "[map_renderer] invalid OPENROADCODE_MAP_PARENT_WINDOW="
                  << parentValue << '\n';
        return;
    }

    Display* display = glfwGetX11Display();
    const Window child = glfwGetX11Window(window);
    if (!display || child == 0) {
        std::cerr << "[map_renderer] GLFW X11 native window is unavailable\n";
        return;
    }

    XWindowAttributes attributes{};
    if (!XGetWindowAttributes(display, static_cast<Window>(parentId), &attributes)) {
        std::cerr << "[map_renderer] X11 parent window " << parentId
                  << " is unavailable\n";
        return;
    }

    XReparentWindow(display, child, static_cast<Window>(parentId), 0, 0);
    XResizeWindow(
        display,
        child,
        static_cast<unsigned int>(attributes.width),
        static_cast<unsigned int>(attributes.height)
    );
    XMapWindow(display, child);
    XFlush(display);

    glfwSetWindowSize(window, attributes.width, attributes.height);
    std::cout << "[map_renderer] embedded in X11 parent " << parentId
              << " size=" << attributes.width << 'x' << attributes.height << '\n';
}
#endif

}

MapView::MapView(
    const mbgl::ResourceOptions&,
    const mbgl::ClientOptions&
)
{
    glfwSetErrorCallback(glfwError);

    if (!glfwInit()) {
        mbgl::Log::Error(mbgl::Event::OpenGL, "Failed to initialize GLFW");
        std::exit(1);
    }

    if (mbgl::gfx::Backend::GetType() == mbgl::gfx::Backend::Type::OpenGL) {
#if MBGL_WITH_EGL
        glfwWindowHint(GLFW_CONTEXT_CREATION_API, GLFW_EGL_CONTEXT_API);
#endif
        glfwWindowHint(GLFW_CLIENT_API, GLFW_OPENGL_ES_API);
        glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 3);
        glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 0);
        glfwWindowHint(GLFW_RED_BITS, 8);
        glfwWindowHint(GLFW_GREEN_BITS, 8);
        glfwWindowHint(GLFW_BLUE_BITS, 8);
        glfwWindowHint(GLFW_ALPHA_BITS, 8);
        glfwWindowHint(GLFW_STENCIL_BITS, 8);
        glfwWindowHint(GLFW_DEPTH_BITS, 16);
    } else {
        glfwWindowHint(GLFW_CLIENT_API, GLFW_NO_API);
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
        mbgl::Log::Error(mbgl::Event::OpenGL, "Failed to create GLFW window");
        std::exit(1);
    }

#if defined(__linux__)
    embedInX11Parent(window);
#endif

    glfwSetWindowUserPointer(window, this);
    glfwSetWindowSizeCallback(window, onWindowResize);
    glfwSetFramebufferSizeCallback(window, onFramebufferResize);
    glfwSetCursorPosCallback(window, onMouseMove);
    glfwSetMouseButtonCallback(window, onMouseClick);
    glfwSetScrollCallback(window, onScroll);

    backend = GLFWBackend::Create(window, true);

    glfwGetWindowSize(window, &width, &height);
    pixelRatio = static_cast<float>(backend->getSize().width) /
                 static_cast<float>(width);

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

mbgl::gfx::RendererBackend& MapView::getRendererBackend()
{
    return backend->getRendererBackend();
}

void MapView::setMap(mbgl::Map* map_)
{
    map = map_;
}

void MapView::setRendererFrontend(MapRendererFrontend* rendererFrontend_)
{
    rendererFrontend = rendererFrontend_;
}

void MapView::setShouldClose()
{
    glfwSetWindowShouldClose(window, GLFW_TRUE);
    glfwPostEmptyEvent();
}

void MapView::onWindowResize(GLFWwindow* window, int width, int height)
{
    auto* view = static_cast<MapView*>(glfwGetWindowUserPointer(window));
    if (!view) {
        return;
    }
    view->width = width;
    view->height = height;
    if (view->map) {
        view->map->setSize({
            static_cast<uint32_t>(width),
            static_cast<uint32_t>(height)
        });
    }
}

void MapView::onFramebufferResize(GLFWwindow* window, int width, int height)
{
    auto* view = static_cast<MapView*>(glfwGetWindowUserPointer(window));
    if (!view) {
        return;
    }
    view->backend->setSize({
        static_cast<uint32_t>(width),
        static_cast<uint32_t>(height)
    });
    view->invalidate();
}

void MapView::onScroll(GLFWwindow* window, double, double yOffset)
{
    auto* view = static_cast<MapView*>(glfwGetWindowUserPointer(window));
    if (!view || !view->map) {
        return;
    }
    const double delta = yOffset * 40.0;
    const double absDelta = std::abs(delta);
    double scale = 2.0 / (1.0 + std::exp(-absDelta / 100.0));
    if (delta < 0.0) {
        scale = 1.0 / scale;
    }
    view->map->scaleBy(
        scale,
        mbgl::ScreenCoordinate{view->lastX, view->lastY}
    );
}

void MapView::onMouseClick(
    GLFWwindow* window,
    int button,
    int action,
    int modifiers
)
{
    auto* view = static_cast<MapView*>(glfwGetWindowUserPointer(window));
    if (!view || !view->map || button != GLFW_MOUSE_BUTTON_LEFT) {
        return;
    }

    view->tracking = action == GLFW_PRESS;
    view->map->setGestureInProgress(view->tracking);

    if (action == GLFW_RELEASE) {
        const double now = glfwGetTime();
        if (now - view->lastClick < 0.4) {
            const double scale = modifiers & GLFW_MOD_SHIFT ? 0.5 : 2.0;
            view->map->scaleBy(
                scale,
                mbgl::ScreenCoordinate{view->lastX, view->lastY},
                mbgl::AnimationOptions{{mbgl::Milliseconds(500)}}
            );
        }
        view->lastClick = now;
    }
}

void MapView::onMouseMove(GLFWwindow* window, double x, double y)
{
    auto* view = static_cast<MapView*>(glfwGetWindowUserPointer(window));
    if (!view || !view->map) {
        return;
    }
    if (view->tracking) {
        const double dx = x - view->lastX;
        const double dy = y - view->lastY;
        if (dx != 0.0 || dy != 0.0) {
            view->map->moveBy(mbgl::ScreenCoordinate{dx, dy});
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
            std::cerr << "[map_renderer] dirty but rendererFrontend is null\n";
            reportedNoRender = true;
        }
        return;
    }
    dirty = false;
    mbgl::gfx::BackendScope scope{backend->getRendererBackend()};
    rendererFrontend->render();
}

void MapView::run()
{
    std::cout << "[map_renderer] entering GLFW event loop\n";
    auto callback = [&]() {
        if (glfwWindowShouldClose(window)) {
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

    frameTick.start(
        mbgl::Duration::zero(),
        mbgl::Milliseconds(1000 / 60),
        callback
    );

#if defined(__APPLE__)
    while (!glfwWindowShouldClose(window)) {
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
