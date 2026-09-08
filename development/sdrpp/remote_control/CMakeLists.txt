cmake_minimum_required(VERSION 3.13)
project(remote_control)

file(GLOB SRC "src/*.cpp")

include(${SDRPP_MODULE_CMAKE})

target_include_directories(remote_control PRIVATE "src/")
