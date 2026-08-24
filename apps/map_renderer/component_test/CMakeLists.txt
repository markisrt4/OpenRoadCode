# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

cmake_minimum_required(VERSION 3.16)
project(openroadcode-map-command-server-test LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(PkgConfig REQUIRED)
pkg_check_modules(ZMQ REQUIRED IMPORTED_TARGET libzmq)

find_path(CPPZMQ_INCLUDE_DIR zmq.hpp REQUIRED)
find_path(RAPIDJSON_INCLUDE_DIR rapidjson/document.h REQUIRED)

add_executable(
    openroadcode-map-command-server-test
    map_command_server_cli.cpp
    ../src/map_command_server.cpp
)

target_include_directories(
    openroadcode-map-command-server-test
    PRIVATE
        ${CPPZMQ_INCLUDE_DIR}
        ${RAPIDJSON_INCLUDE_DIR}
        ../src
)

target_link_libraries(
    openroadcode-map-command-server-test
    PRIVATE
        PkgConfig::ZMQ
)
