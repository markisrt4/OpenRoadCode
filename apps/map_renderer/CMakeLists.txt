cmake_minimum_required(VERSION 3.20)

project(openroadcode_map_renderer LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

#
# MapLibre Native checkout
#
set(MAPLIBRE_ROOT
    "/src/maplibre-native"
    CACHE PATH
    "Path to MapLibre Native source tree"
)

set(MAPLIBRE_BUILD
    "${MAPLIBRE_ROOT}/build-linux-opengl"
    CACHE PATH
    "Path to MapLibre Native build tree"
)


add_executable(openroadcode-map-renderer
    src/main.cpp
    src/map_view.cpp
    src/map_renderer_frontend.cpp
    src/map_command_server.cpp

    ${MAPLIBRE_ROOT}/platform/glfw/glfw_gl_backend.cpp
)

target_include_directories(openroadcode-map-renderer PRIVATE
    ${MAPLIBRE_ROOT}/include
    ${MAPLIBRE_ROOT}/src
    ${MAPLIBRE_ROOT}/platform/default/include
    ${MAPLIBRE_ROOT}/platform/glfw

    ${MAPLIBRE_ROOT}/vendor/unordered_dense/include
    ${MAPLIBRE_ROOT}/vendor/maplibre-native-base/include
    ${MAPLIBRE_ROOT}/vendor/maplibre-native-base/deps/geometry.hpp/include
    ${MAPLIBRE_ROOT}/vendor/maplibre-native-base/deps/geojson.hpp/include
    ${MAPLIBRE_ROOT}/vendor/maplibre-native-base/deps/variant/include
    ${MAPLIBRE_ROOT}/vendor/maplibre-native-base/deps/cheap-ruler-cpp/include
    ${MAPLIBRE_ROOT}/vendor/rapidjson/include
)

target_compile_definitions(openroadcode-map-renderer PRIVATE
    EGL_NO_X11
    MBGL_WITH_EGL=1
    MESA_EGL_NO_X11_HEADERS
    MLN_RENDER_BACKEND_OPENGL=1
    MLN_USE_UNORDERED_DENSE=1
    MLN_WITH_WAYLAND=1
    RAPIDJSON_HAS_STDSTRING=1
    WL_EGL_PLATFORM
)

target_compile_options(openroadcode-map-renderer PRIVATE
    -fno-rtti
)

target_link_directories(openroadcode-map-renderer PRIVATE
    ${MAPLIBRE_BUILD}
)

target_link_libraries(openroadcode-map-renderer PRIVATE
    glfw

    ${MAPLIBRE_BUILD}/libmbgl-core.a
    ${MAPLIBRE_BUILD}/libmbgl-vendor-parsedate.a
    ${MAPLIBRE_BUILD}/vendor/maplibre-tile-spec/cpp/libmlt-cpp.a
    ${MAPLIBRE_BUILD}/vendor/maplibre-tile-spec/cpp/libfastpfor-lib.a
    ${MAPLIBRE_BUILD}/libmbgl-vendor-csscolorparser.a
    ${MAPLIBRE_BUILD}/libmbgl-harfbuzz.a
    ${MAPLIBRE_BUILD}/libmbgl-freetype.a
    ${MAPLIBRE_BUILD}/libmbgl-vendor-nunicode.a
    ${MAPLIBRE_BUILD}/libmbgl-vendor-sqlite.a

    EGL
    GLESv2
    curl
    jpeg
    uv
    pthread
    dl
    rt
    webp
    icuuc
    icudata
    icui18n
    png
    z
    GLX
    OpenGL
)
