cmake_minimum_required(VERSION 3.20)
project(fallgorithm_native LANGUAGES CXX)

# A C++ translation of the Python reach_plan agent (Experiment 011). The Python
# modules stay the reference; tests/test_native.py checks that both agree.

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

set(BLOCK_STACK_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../block-stack" CACHE PATH
    "Block Stack checkout whose blocks_core library the game loop links")
set(BLOCK_STACK_BUILD_APP OFF)
set(BLOCK_STACK_BUILD_PYTHON OFF)
set(BLOCK_STACK_BUILD_TESTS OFF)
add_subdirectory("${BLOCK_STACK_ROOT}" block-stack EXCLUDE_FROM_ALL)

add_library(fallgorithm_native SHARED c_api.cpp net.cpp)
target_link_libraries(fallgorithm_native PRIVATE blocks_core)
set_target_properties(fallgorithm_native PROPERTIES CXX_VISIBILITY_PRESET hidden
                      VISIBILITY_INLINES_HIDDEN ON)
if(MSVC)
    target_compile_options(fallgorithm_native PRIVATE /W4 /fp:precise)
else()
    # Python adds and multiplies doubles one operation at a time. A fused
    # multiply-add rounds once instead of twice, so it is never allowed here:
    # the C++ must compute exactly the same values. No -ffast-math either.
    target_compile_options(fallgorithm_native PRIVATE -Wall -Wextra -Wpedantic -fno-fast-math -ffp-contract=off)
endif()

# Experiment 020's value network has no Python twin, so the rule above does not bind it:
# float32 with fused multiply-adds and the host's vector instructions. These options come
# after the target's, so they win for net.cpp alone.
if(NOT MSVC)
    set_source_files_properties(net.cpp PROPERTIES COMPILE_OPTIONS "-O3;-march=native;-ffp-contract=fast")
endif()
