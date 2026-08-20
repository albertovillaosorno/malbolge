// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Native command-line composition for one normalized C frontend request.
// - Must-Not:
//   - Interpret C semantics, expose input host paths, or choose downstream IR.
// - Allows:
//   - Inputs: private build/runtime roots, a logical source ID, and source
//     file.
//   - Outputs: normalized JSON on stdout or stable diagnostics on stderr.
//   - Side effects: reads only the explicitly selected source file.
// - Split-When:
//   - A library/server frontend gains independent process lifecycle.
// - Merge-When:
//   - One native executable remains the only frontend composition entrypoint.
// - Summary:
//   - Wires file input and private tool roots into the host-neutral frontend.
// - Description:
//   - The physical source path is never copied into the normalized artifact.
// - Usage:
//   - Built by the pinned LLVM frontend build projection and used by tests.
// - Defaults:
//   - Missing or duplicate arguments fail before source parsing.
//

//! Command-line composition for deterministic C frontend normalization.

#include "../port-inbound/frontend.hpp"

#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <optional>
#include <string>
#include <string_view>

namespace {

using malbolge::compiler::c_frontend::FrontendRequest;
using malbolge::compiler::c_frontend::FrontendResult;

struct Arguments final {
  std::string guest_include;
  std::string input;
  std::string resource_dir;
  std::string source_id;
};

[[nodiscard]] std::optional<Arguments> parse_arguments(int argc, char **argv) {
  Arguments result;
  for (int index = 1; index < argc; ++index) {
    const std::string_view argument(argv[index]);
    auto value = [&](std::string &destination) -> bool {
      if (!destination.empty() || index + 1 >= argc) {
        return false;
      }
      destination = argv[++index];
      return !destination.empty();
    };
    if (argument == "--guest-include") {
      if (!value(result.guest_include)) {
        return std::nullopt;
      }
    } else if (argument == "--resource-dir") {
      if (!value(result.resource_dir)) {
        return std::nullopt;
      }
    } else if (argument == "--source-id") {
      if (!value(result.source_id)) {
        return std::nullopt;
      }
    } else if (!argument.starts_with("-") && result.input.empty()) {
      result.input = argument;
    } else {
      return std::nullopt;
    }
  }
  if (result.guest_include.empty() || result.input.empty() ||
      result.resource_dir.empty() || result.source_id.empty()) {
    return std::nullopt;
  }
  return result;
}

[[nodiscard]] std::optional<std::string> read_source(const std::string &path) {
  std::ifstream input(std::filesystem::path(path), std::ios::binary);
  if (!input) {
    return std::nullopt;
  }
  return std::string(std::istreambuf_iterator<char>(input),
                     std::istreambuf_iterator<char>());
}

} // namespace

int main(int argc, char **argv) {
  if (argc == 2 && std::string_view(argv[1]) == "--version") {
    std::cout << "malbolge-c-frontend 1 LLVM 22.1.8\n";
    return 0;
  }
  const auto arguments = parse_arguments(argc, argv);
  if (!arguments.has_value()) {
    std::cerr << "MALBOLGE-FRONTEND-003 invalid command line\n";
    return 2;
  }
  const auto source = read_source(arguments->input);
  if (!source.has_value()) {
    std::cerr << "MALBOLGE-FRONTEND-003 cannot read selected source\n";
    return 2;
  }
  const FrontendResult result =
      malbolge::compiler::c_frontend::normalize_c_source(FrontendRequest{
          arguments->guest_include,
          arguments->resource_dir,
          arguments->source_id,
          *source,
      });
  if (result.status != 0) {
    std::cerr << result.diagnostic << '\n';
    return result.status;
  }
  std::cout << result.artifact << '\n';
  return 0;
}
