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
//   - Project clang-tidy host wiring and Windows registry-bridge export.
// - Must-Not:
//   - Implement guest-C policy or discover an ambient LLVM installation.
// - Allows:
//   - Inputs: clang-tidy command-line arguments and loaded extension modules.
//   - Outputs: clang-tidy diagnostics and standard process status.
//   - Side effects: dynamic module loading requested by clang-tidy arguments.
// - Split-When:
//   - Split when host wiring gains a second independently versioned platform.
// - Merge-When:
//   - Merge when upstream clang-tidy exports the required registry ABI itself.
// - Summary:
//   - Host pinned clang-tidy with one explicit Windows plugin registry bridge.
// - Description:
//   - Reuses clangTidyMain and exports only the reviewed registry operation.
// - Usage:
//   - Built through tools/tidy against the exact pinned LLVM development kit.
// - Defaults:
//   - Guest validation supplies its pinned Clang resource directory explicitly.
//

//! Pinned clang-tidy host with the project Windows registry bridge.

#include "clang-tidy/ClangTidyModule.h"
#include "clang-tidy/tool/ClangTidyMain.h"

extern "C" __declspec(dllexport) void
malbolge_tidy_register_node(clang::tidy::ClangTidyModuleRegistry::node *Node) {
  clang::tidy::ClangTidyModuleRegistry::add_node(Node);
}

int main(int argc, const char **argv) {
  return clang::tidy::clangTidyMain(argc, argv);
}
