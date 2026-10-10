// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT

#pragma once

#include <optional>

struct EmbeddedSize {
    int width = 0;
    int height = 0;

    bool differsFrom(EmbeddedSize other) const {
        return width != other.width || height != other.height;
    }
};

struct EmbeddedResizePlan {
    EmbeddedSize target;
    bool resizeWindow;
    bool resizeMap;
    bool resizeFramebuffer;
};

// The X11 parent allocation is authoritative. A correctly sized native window
// does not establish that GLFW callbacks updated MapLibre's cached viewports.
inline std::optional<EmbeddedResizePlan> planEmbeddedResize(
    EmbeddedSize parent, EmbeddedSize nativeWindow,
    EmbeddedSize map, EmbeddedSize framebuffer) {
    if (parent.width < 1 || parent.height < 1)
        return std::nullopt;
    return EmbeddedResizePlan{
        parent, parent.differsFrom(nativeWindow), parent.differsFrom(map),
        parent.differsFrom(framebuffer),
    };
}
