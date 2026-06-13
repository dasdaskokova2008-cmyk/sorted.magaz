cmake_minimum_required(VERSION 3.15)
project(external_sort LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Python COMPONENTS Interpreter Development REQUIRED)
find_package(pybind11 CONFIG REQUIRED)

pybind11_add_module(external_sort_cpp
    cpp/bindings.cpp
    cpp/external_sort.cpp
)

target_include_directories(external_sort_cpp PRIVATE cpp)
