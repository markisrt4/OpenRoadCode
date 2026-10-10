// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT

#include "../src/embedded_resize.hpp"
#include <iostream>
#include <stdexcept>

void require(bool condition, const char* message) {
    if (!condition)
        throw std::runtime_error(message);
}

int main() {
    const EmbeddedSize expanded{900, 500};
    const EmbeddedSize contracted{690, 500};
    auto plan = planEmbeddedResize(expanded, expanded, contracted, contracted);
    require(plan.has_value() && !plan->resizeWindow, "Native window already fits");
    require(plan->resizeMap && plan->resizeFramebuffer,
            "Lost callbacks must not leave stale MapLibre viewports");

    plan = planEmbeddedResize(expanded, expanded, expanded, contracted);
    require(plan && !plan->resizeMap && plan->resizeFramebuffer,
            "Repair a missing framebuffer callback independently");
    plan = planEmbeddedResize(expanded, expanded, contracted, expanded);
    require(plan && plan->resizeMap && !plan->resizeFramebuffer,
            "Repair a missing map-size callback independently");
    plan = planEmbeddedResize(expanded, contracted, expanded, expanded);
    require(plan && plan->resizeWindow && !plan->resizeMap && !plan->resizeFramebuffer,
            "Repair native geometry even when cached sizes already match");

    EmbeddedSize native = expanded, map = expanded, framebuffer = expanded;
    for (int cycle = 0; cycle < 12; ++cycle) {
        const auto target = cycle % 2 == 0 ? contracted : expanded;
        // Simulate a native ConfigureNotify update with both callbacks missing.
        native = target;
        plan = planEmbeddedResize(target, native, map, framebuffer);
        require(plan && !plan->resizeWindow && plan->resizeMap && plan->resizeFramebuffer,
                "Every collapse/expand must repair stale caches");
        map = plan->target;
        framebuffer = plan->target;
        const auto stable = planEmbeddedResize(target, native, map, framebuffer);
        require(stable && !stable->resizeWindow && !stable->resizeMap && !stable->resizeFramebuffer,
                "Stable allocations must not trigger continuous redraws");
    }

    plan = planEmbeddedResize({900, 650}, expanded, expanded, expanded);
    require(plan && plan->resizeWindow && plan->resizeMap && plan->resizeFramebuffer,
            "Height-only changes must update all dimensions");
    require(!planEmbeddedResize({0, 500}, expanded, expanded, expanded), "Ignore zero width");
    require(!planEmbeddedResize({900, 0}, expanded, expanded, expanded), "Ignore zero height");
    require(!planEmbeddedResize({-1, 500}, expanded, expanded, expanded), "Ignore invalid sizes");
    std::cout << "Embedded resize regression checks passed\n";
}
