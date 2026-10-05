# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

cmake_minimum_required(VERSION 3.16)
project(openroadcode-map-command-server-test LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(PkgConfig REQUIRED)
find_package(spdlog REQUIRED)
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
        spdlog::spdlog
)

# This contract gate compiles without MapLibre or a graphical display.
add_executable(openroadcode-logging-contract-test logging_contract_cli.cpp)
target_include_directories(openroadcode-logging-contract-test PRIVATE
    ${RAPIDJSON_INCLUDE_DIR} ../src)
target_link_libraries(openroadcode-logging-contract-test PRIVATE spdlog::spdlog)

include(CTest)
if(BUILD_TESTING)
    find_package(Python3 REQUIRED COMPONENTS Interpreter)
    add_test(NAME logging-contract
        COMMAND ${Python3_EXECUTABLE}
            ${CMAKE_CURRENT_SOURCE_DIR}/check_logging_contract.py
            $<TARGET_FILE:openroadcode-logging-contract-test>)
endif()
