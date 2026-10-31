// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - Apache-2.0
// Confidential:
//   - false
// License-File:
//   - LICENSE
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

#include <algorithm>
#include <array>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <memory>
#include <optional>
#include <string>
#include <string_view>

#if defined(__linux__) || defined(__ANDROID__)
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#endif

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

// The frontend owns host-side acquisition, not an unbounded source stream.
// A 64 MiB ceiling is independent of the guest machine's memory geometry.
constexpr std::size_t kMaxSourceBytes = 64U * 1024U * 1024U;
constexpr std::size_t kSourceReadChunk = 64U * 1024U;

#if defined(__linux__) || defined(__ANDROID__)
[[nodiscard]] bool same_source_inode(const struct stat &first,
                                     const struct stat &second) {
  return S_ISREG(first.st_mode) && S_ISREG(second.st_mode) &&
         first.st_dev == second.st_dev && first.st_ino == second.st_ino &&
         first.st_size == second.st_size &&
         first.st_mtim.tv_sec == second.st_mtim.tv_sec &&
         first.st_mtim.tv_nsec == second.st_mtim.tv_nsec &&
         first.st_ctim.tv_sec == second.st_ctim.tv_sec &&
         first.st_ctim.tv_nsec == second.st_ctim.tv_nsec;
}
#endif

[[nodiscard]] std::optional<std::string> read_source(const std::string &path) {
#if defined(__linux__) || defined(__ANDROID__)
  // Opening nonblocking avoids waiting forever for a FIFO writer, including
  // when the supplied path is a symlink to a FIFO. Inspect this same handle.
  const int descriptor =
      ::open(path.c_str(), O_RDONLY | O_NONBLOCK | O_CLOEXEC);
  if (descriptor < 0) {
    return std::nullopt;
  }
  std::unique_ptr<std::FILE, decltype(&std::fclose)> input(
      ::fdopen(descriptor, "rb"), &std::fclose);
  if (!input) {
    (void)::close(descriptor);
    return std::nullopt;
  }
  struct stat initial{};
  if (::fstat(::fileno(input.get()), &initial) != 0 ||
      !S_ISREG(initial.st_mode) || initial.st_size < 0 ||
      static_cast<std::uintmax_t>(initial.st_size) > kMaxSourceBytes) {
    return std::nullopt;
  }
#else
  std::error_code error;
  const auto size = std::filesystem::file_size(path, error);
  if (error || size > kMaxSourceBytes ||
      !std::filesystem::is_regular_file(path, error) || error) {
    return std::nullopt;
  }
  std::ifstream input(std::filesystem::path(path), std::ios::binary);
  if (!input) {
    return std::nullopt;
  }
#endif
  std::string bytes;
#if defined(__linux__) || defined(__ANDROID__)
  bytes.reserve(static_cast<std::size_t>(initial.st_size));
#else
  bytes.reserve(static_cast<std::size_t>(size));
#endif
  std::array<char, kSourceReadChunk> chunk{};
  while (bytes.size() <= kMaxSourceBytes) {
    const auto remaining = kMaxSourceBytes + 1U - bytes.size();
    const auto requested = std::min(chunk.size(), remaining);
#if defined(__linux__) || defined(__ANDROID__)
    const auto count = std::fread(chunk.data(), 1, requested, input.get());
    if (count == 0) {
      if (std::ferror(input.get()) != 0) {
        return std::nullopt;
      }
      break;
    }
#else
    input.read(chunk.data(), static_cast<std::streamsize>(requested));
    const auto count = static_cast<std::size_t>(input.gcount());
    if (input.bad() || (count == 0 && !input.eof())) {
      return std::nullopt;
    }
    if (count == 0) {
      break;
    }
#endif
    bytes.append(chunk.data(), count);
  }
#if defined(__linux__) || defined(__ANDROID__)
  struct stat opened_after{};
  struct stat named_after{};
  if (bytes.size() > kMaxSourceBytes ||
      bytes.size() != static_cast<std::size_t>(initial.st_size) ||
      ::fstat(::fileno(input.get()), &opened_after) != 0 ||
      ::stat(path.c_str(), &named_after) != 0 ||
      !same_source_inode(initial, opened_after) ||
      !same_source_inode(initial, named_after)) {
    return std::nullopt;
  }
#else
  const auto final_size = std::filesystem::file_size(path, error);
  if (bytes.size() > kMaxSourceBytes || bytes.size() != size || error ||
      final_size != size || !std::filesystem::is_regular_file(path, error) ||
      error) {
    return std::nullopt;
  }
#endif
  return bytes;
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
