#pragma once

#include <mbgl/map/map.hpp>
#include <mbgl/util/run_loop.hpp>
#include <mbgl/util/timer.hpp>

#include <memory>
#include <functional>

struct GLFWwindow;
class GLFWBackend;
class MapRendererFrontend;

namespace mbgl {
namespace gfx {
class RendererBackend;
}
}

/**
 * @brief GLFW window, input adapter, and event loop for a MapLibre map.
 *
 * The view owns the graphics backend and translates window resize, mouse,
 * scroll, and frame events into MapLibre operations.
 */
class MapView : public mbgl::MapObserver {
public:
    /**
     * @brief Create the renderer window and graphics backend.
     * @param resourceOptions MapLibre resource configuration.
     * @param clientOptions MapLibre client configuration.
     */
    MapView(
        const mbgl::ResourceOptions& resourceOptions,
        const mbgl::ClientOptions& clientOptions
    );

    /** @brief Destroy the window and terminate GLFW. */
    ~MapView() override;

    /** @brief Return the framebuffer-to-window pixel ratio. */
    float getPixelRatio() const;

    /** @brief Return the current logical window size. */
    mbgl::Size getSize() const;

    /** @brief Return the graphics backend used by the renderer. */
    mbgl::gfx::RendererBackend& getRendererBackend();

    /** @brief Attach the MapLibre map controlled by this view. */
    void setMap(mbgl::Map* map);

    /** @brief Attach the frontend that renders invalidated frames. */
    void setRendererFrontend(MapRendererFrontend* rendererFrontend);

    /** @brief Run the window event loop until the window closes. */
    void run();

    /** @brief Mark the view dirty and wake the event loop. */
    void invalidate();

    /** @brief Request that the window and event loop close. */
    void setShouldClose();

    /** @brief Receive notification that MapLibre will render a frame. */
    void onWillStartRenderingFrame() override;

    /**
     * @brief Set work to execute on every event-loop tick.
     * @param callback Callback used to poll external map commands.
     */
    void setUpdateCallback(std::function<void()> callback);

private:
    static void onWindowResize(
        GLFWwindow* window,
        int width,
        int height
    );

    static void onFramebufferResize(
        GLFWwindow* window,
        int width,
        int height
    );

    static void onScroll(
        GLFWwindow* window,
        double xOffset,
        double yOffset
    );

    static void onMouseClick(
        GLFWwindow* window,
        int button,
        int action,
        int modifiers
    );

    static void onMouseMove(
        GLFWwindow* window,
        double x,
        double y
    );

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
    double lastClick = -1.0;

    bool tracking = false;
    bool dirty = false;

    mbgl::util::RunLoop runLoop;
    mbgl::util::Timer frameTick;
    
    std::function<void()> updateCallback;
};
