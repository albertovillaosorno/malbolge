// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Host-neutral request/result contract for one C frontend normalization.
// - Must-Not:
//   - Expose Clang C++ types, native paths in artifacts, or downstream IR.
// - Allows:
//   - Inputs: source bytes, a portable identity, and private include roots.
//   - Outputs: one deterministic normalized artifact or stable failure text.
//   - Side effects: none beyond memory owned by the implementation.
// - Split-When:
//   - Incremental or multi-translation-unit parsing requires new lifetimes.
// - Merge-When:
//   - One frontend entry contract remains sufficient for supported C input.
// - Summary:
//   - Defines the compiler-facing entry boundary for normalized C semantics.
// - Description:
//   - Build/runtime paths are inputs but are deliberately absent from output.
// - Usage:
//   - Implemented by the pinned-Clang inbound adapter and called by
//   composition.
// - Defaults:
//   - Any malformed request fails closed before invoking Clang.
//

#ifndef MALBOLGE_COMPILER_C_FRONTEND_PORT_INBOUND_FRONTEND_HPP
#define MALBOLGE_COMPILER_C_FRONTEND_PORT_INBOUND_FRONTEND_HPP

#include <string>

namespace malbolge::compiler::c_frontend {

struct FrontendRequest final {
  std::string guest_include;
  std::string resource_dir;
  std::string source_id;
  std::string source_text;
};

struct FrontendResult final {
  std::string artifact;
  std::string diagnostic;
  int status = 1;
};

[[nodiscard]] FrontendResult normalize_c_source(const FrontendRequest &request);

} // namespace malbolge::compiler::c_frontend

#endif
