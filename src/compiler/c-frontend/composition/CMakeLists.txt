# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT

cmake_minimum_required(VERSION 3.20)
project(MalbolgeCFrontend LANGUAGES CXX)

if(NOT WIN32 OR NOT MSVC)
  message(FATAL_ERROR "Malbolge C frontend currently requires Windows MSVC ABI")
endif()

set(MALBOLGE_LLVM_ROOT "" CACHE PATH "LLVM 22.1.8 development archive root")
set(MALBOLGE_DIA_GUIDS "" CACHE FILEPATH "Local x64 diaguids.lib")
set(MALBOLGE_OUTPUT_DIR "" CACHE PATH "Repository-local C frontend output")
if(NOT MALBOLGE_LLVM_ROOT OR NOT MALBOLGE_OUTPUT_DIR)
  message(FATAL_ERROR "MALBOLGE_LLVM_ROOT and MALBOLGE_OUTPUT_DIR are required")
endif()

find_package(LLVM 22.1.8 EXACT REQUIRED CONFIG
  PATHS "${MALBOLGE_LLVM_ROOT}/lib/cmake/llvm"
  NO_DEFAULT_PATH)

if(NOT EXISTS "${MALBOLGE_DIA_GUIDS}")
  message(FATAL_ERROR "MALBOLGE_DIA_GUIDS must name local x64 diaguids.lib")
endif()
get_target_property(_malbolge_pdb_links
  LLVMDebugInfoPDB INTERFACE_LINK_LIBRARIES)
list(GET _malbolge_pdb_links 0 _malbolge_packaged_dia)
if(NOT _malbolge_packaged_dia MATCHES "diaguids\.lib$")
  message(FATAL_ERROR "LLVM PDB target no longer exposes expected DIA link")
endif()
list(REMOVE_AT _malbolge_pdb_links 0)
list(PREPEND _malbolge_pdb_links "${MALBOLGE_DIA_GUIDS}")
set_property(TARGET LLVMDebugInfoPDB PROPERTY
  INTERFACE_LINK_LIBRARIES "${_malbolge_pdb_links}")

find_package(Clang 22.1.8 EXACT REQUIRED CONFIG
  PATHS "${MALBOLGE_LLVM_ROOT}/lib/cmake/clang"
  NO_DEFAULT_PATH)

add_executable(
  malbolge-c-frontend
  ../adapter-inbound/clang_frontend.cpp
  malbolge_c_frontend.cpp)
target_compile_features(malbolge-c-frontend PRIVATE cxx_std_20)
target_compile_options(malbolge-c-frontend PRIVATE /W4 /WX)
target_include_directories(malbolge-c-frontend SYSTEM PRIVATE
  ${LLVM_INCLUDE_DIRS}
  ${CLANG_INCLUDE_DIRS})
target_link_libraries(malbolge-c-frontend PRIVATE clangTooling)
target_link_options(malbolge-c-frontend PRIVATE /Brepro)
set_target_properties(malbolge-c-frontend PROPERTIES
  RUNTIME_OUTPUT_DIRECTORY "${MALBOLGE_OUTPUT_DIR}/bin")
