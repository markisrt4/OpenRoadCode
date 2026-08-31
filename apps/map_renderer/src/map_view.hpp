// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT

#pragma once

#include <mbgl/map/map.hpp>
#include <mbgl/util/run_loop.hpp>
#include <mbgl/util/timer.hpp>

#include <memory>
#include <functional>
#include <string>

struct GLFWwindow;
class GLFWBackend;
class MapRendererFrontend;

namespace mbgl {
namespace gfx {
class RendererBackend;
}
}

class MapView : public mbgl::MapObserver {
public:
    using PoiSelectedCallback = std::function<void(
        const std::string& name,
        const std::string& brand,
        double latitude,
        double longitude
    )>;

    MapView(
        const mbgl::ResourceOptions& resourceOptions,
        const mbgl::ClientOptions& clientOptions
    );
    ~MapView() override;

    float getPixelRatio() const;
    mbgl::Size getSize() const;
    mbgl::gfx::RendererBackend& getRendererBackend();
    void setMap(mbgl::Map* map);
    void setRendererFrontend(MapRendererFrontend* rendererFrontend);
    void run();
    void invalidate();
    void setShouldClose();
    void onWillStartRenderingFrame() override;
    void setUpdateCallback(std::function<void()> callback);
    void setPoiSelectedCallback(PoiSelectedCallback callback);

private:
    static void onWindowResize(GLFWwindow* window, int width, int height);
    static void onFramebufferResize(GLFWwindow* window, int width, int height);
    static void onScroll(GLFWwindow* window, double xOffset, double yOffset);
    static void onMouseClick(GLFWwindow* window, int button, int action, int modifiers);
    static void onMouseMove(GLFWwindow* window, double x, double y);
    void selectPoiAt(double x, double y);
    void render();

    mbgl::Map* map = nullptr;
    MapRendererFrontend* rendererFrontend = nullptr;
    std::unique_ptr<GLFWBackend> backend;
    GLFWwindow* window = nullptr;
    int width = 1024;
    int height = 600;
    float pixelRatio = 1.0f;
    double lastX = 0.0;
    double lastY = 0.0;
    double pressX = 0.0;
    double pressY = 0.0;
    double lastClick = -1.0;
    bool tracking = false;
    bool dirty = false;
    mbgl::util::RunLoop runLoop;
    mbgl::util::Timer frameTick;
    std::function<void()> updateCallback;
    PoiSelectedCallback poiSelectedCallback;
};
