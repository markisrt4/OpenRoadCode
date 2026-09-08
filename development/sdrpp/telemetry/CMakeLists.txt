cmake_minimum_required(VERSION 3.13)
project(telemetry)

file(GLOB SRC "src/*.cpp")

include(${SDRPP_MODULE_CMAKE})

target_include_directories(telemetry PRIVATE "src/")
