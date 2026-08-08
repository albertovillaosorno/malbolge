# Clang-Tidy Extensible Checks

## Status

Verified; evidence verified against LLVM 22.1.8 on 2026-08-08.

## Subject

- Canonical name: clang-tidy
- Subject class: Static analysis and lint framework
- Stable identifier: LLVM Extra Clang Tools clang-tidy
- Publisher or authority: LLVM Project

## Repository Use

`tools/tidy` builds the project-owned out-of-tree clang-tidy plugin and the
Windows host required to load that plugin against exactly LLVM 22.1.8. The
plugin extends the explicit guest-C compatibility boundary without forking
Clang or replacing the stock analyzer profile.

## Provenance

Official clang-tidy documentation describes the tool as an extensible framework
for diagnostics and fixes. Official contributing documentation describes
out-of-tree check plugins as shared libraries loaded with `-load` and states
that the plugin must be compiled against the same clang-tidy version because
there are no API or ABI stability guarantees for this interface.

LLVM 22.1.8 release metadata identifies the reviewed Windows development archive
used by the repository. The repository tracks the exact asset size and SHA-256
in `llvm-clang-tidy-toolchain.json`.

## Identity And Version

- Canonical name: clang-tidy
- Subject class: Static analysis and lint framework
- Stable identifier: LLVM Extra Clang Tools clang-tidy
- Publisher or authority: LLVM Project
- Repository version: LLVM `22.1.8`
- Release tag: `llvmorg-22.1.8`

## License Or Terms

This is external material. Citation does not relicense the source or import its
terms into the repository MIT license.

## Evidence

### Verified

- clang-tidy is based on Clang/LibTooling.
- Checks are modular and selectable by check-name patterns.
- Out-of-tree check plugins are shared libraries loaded by clang-tidy.
- Out-of-tree plugin code must match the exact clang-tidy API/ABI version.
- The LLVM 22.1.8 Windows development archive contains the clang-tidy headers,
  static libraries, LLVM/Clang CMake metadata, and build tools needed here.
- The official LLVM 22.1.8 Windows executable does not provide the registry
  export needed by this out-of-tree DLL layout, so the repository relinks the
  same pinned `clangTidyMain` libraries behind one narrow registry bridge.

### Unresolved

The lane-7 plugin implements the closed guest ABI source-exclusion check set.
Complete guest language, libc/runtime, determinism, resource, and compiler
lowerability coverage remains governed by later TODO contracts.

## Sources

- <https://clang.llvm.org/extra/clang-tidy/index.html> - accessed 2026-08-08.
- <https://clang.llvm.org/extra/clang-tidy/Contributing.html> - accessed
  2026-08-08.
- <https://github.com/llvm/llvm-project/releases/tag/llvmorg-22.1.8> - accessed
  2026-08-08.
