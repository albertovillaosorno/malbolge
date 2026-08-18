# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT

cmake_minimum_required(VERSION 3.20)
project(MalbolgeClangTidy LANGUAGES CXX)

set(MALBOLGE_OUTPUT_DIR "" CACHE PATH "Repository-local native-analysis output")
if(NOT MALBOLGE_OUTPUT_DIR)
  message(FATAL_ERROR "MALBOLGE_OUTPUT_DIR is required")
endif()

set(_malbolge_module_source
  ../../../src/tooling/native-analysis/adapter-inbound/malbolge_tidy_module.cpp)

if(WIN32)
  if(NOT MSVC)
    message(FATAL_ERROR "Malbolge Windows clang-tidy requires the MSVC ABI")
  endif()

  set(MALBOLGE_LLVM_ROOT "" CACHE PATH "LLVM 22.1.8 development archive root")
  set(MALBOLGE_DIA_GUIDS "" CACHE FILEPATH "Local x64 diaguids.lib")
  if(NOT MALBOLGE_LLVM_ROOT)
    message(FATAL_ERROR "MALBOLGE_LLVM_ROOT is required on Windows")
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
  if(NOT _malbolge_packaged_dia MATCHES "diaguids\\.lib$")
    message(FATAL_ERROR
      "LLVM 22.1.8 PDB target no longer exposes expected DIA link")
  endif()
  list(REMOVE_AT _malbolge_pdb_links 0)
  list(PREPEND _malbolge_pdb_links "${MALBOLGE_DIA_GUIDS}")
  set_property(TARGET LLVMDebugInfoPDB PROPERTY
    INTERFACE_LINK_LIBRARIES "${_malbolge_pdb_links}")

  find_package(Clang 22.1.8 EXACT REQUIRED CONFIG
    PATHS "${MALBOLGE_LLVM_ROOT}/lib/cmake/clang"
    NO_DEFAULT_PATH)

  add_executable(
    malbolge-clang-tidy
    ../../../src/tooling/native-analysis/composition/malbolge_clang_tidy.cpp)
  target_compile_features(malbolge-clang-tidy PRIVATE cxx_std_20)
  target_include_directories(malbolge-clang-tidy SYSTEM PRIVATE
    ${LLVM_INCLUDE_DIRS}
    ${CLANG_INCLUDE_DIRS})
  target_link_libraries(malbolge-clang-tidy PRIVATE clangTidyMain)
  target_link_options(malbolge-clang-tidy PRIVATE /Brepro)
  set_target_properties(malbolge-clang-tidy PROPERTIES
    ENABLE_EXPORTS ON
    RUNTIME_OUTPUT_DIRECTORY "${MALBOLGE_OUTPUT_DIR}/bin")

  add_library(malbolge-tidy MODULE ${_malbolge_module_source})
  target_compile_features(malbolge-tidy PRIVATE cxx_std_20)
  target_include_directories(malbolge-tidy SYSTEM PRIVATE
    ${LLVM_INCLUDE_DIRS}
    ${CLANG_INCLUDE_DIRS})
  target_link_libraries(malbolge-tidy PRIVATE
    clangTidy
    clangASTMatchers
    clangAST
    clangBasic)
  target_link_options(malbolge-tidy PRIVATE /Brepro)
  set_target_properties(malbolge-tidy PROPERTIES
    PREFIX ""
    LIBRARY_OUTPUT_DIRECTORY "${MALBOLGE_OUTPUT_DIR}/bin"
    RUNTIME_OUTPUT_DIRECTORY "${MALBOLGE_OUTPUT_DIR}/bin")
elseif(UNIX AND NOT APPLE)
  set(MALBOLGE_LLVM_DEVELOPMENT_ROOT "" CACHE PATH
    "Repository-local LLVM 22.1.8 development root")
  set(MALBOLGE_LLVM_RUNTIME_ROOT "" CACHE PATH
    "Repository-local LLVM 22.1.8 runtime root")
  if(NOT MALBOLGE_LLVM_DEVELOPMENT_ROOT OR NOT MALBOLGE_LLVM_RUNTIME_ROOT)
    message(FATAL_ERROR
      "Linux requires local LLVM development and runtime roots")
  endif()

  set(_malbolge_clang_cpp
    "${MALBOLGE_LLVM_RUNTIME_ROOT}/lib/libclang-cpp.so.22.1")
  set(_malbolge_llvm
    "${MALBOLGE_LLVM_RUNTIME_ROOT}/lib/libLLVM.so.22.1")
  foreach(_malbolge_required
      "${MALBOLGE_LLVM_DEVELOPMENT_ROOT}/include/clang-tidy/ClangTidyModule.h"
      "${_malbolge_clang_cpp}"
      "${_malbolge_llvm}")
    if(NOT EXISTS "${_malbolge_required}")
      message(FATAL_ERROR
        "Missing exact Linux LLVM input: ${_malbolge_required}")
    endif()
  endforeach()

  add_library(malbolge-tidy MODULE ${_malbolge_module_source})
  target_compile_features(malbolge-tidy PRIVATE cxx_std_20)
  target_include_directories(malbolge-tidy SYSTEM PRIVATE
    "${MALBOLGE_LLVM_DEVELOPMENT_ROOT}/include")
  target_link_libraries(malbolge-tidy PRIVATE
    "${_malbolge_clang_cpp}"
    "${_malbolge_llvm}")
  target_compile_options(malbolge-tidy PRIVATE -Wall -Wextra -Werror)
  set_target_properties(malbolge-tidy PROPERTIES
    PREFIX ""
    OUTPUT_NAME "malbolge-tidy"
    LIBRARY_OUTPUT_DIRECTORY "${MALBOLGE_OUTPUT_DIR}/bin")
else()
  message(FATAL_ERROR "Unsupported Malbolge clang-tidy build platform")
endif()
