# Clang-Tidy Extensible Checks

## Status

Verified; evidence verified.

## Subject

- Canonical name: clang-tidy
- Subject class: Static analysis and lint framework
- Stable identifier: LLVM Extra Clang Tools clang-tidy
- Publisher or authority: LLVM Project

## Repository Use

`malbolge-tidy` is planned as an out-of-tree clang-tidy plugin that expresses
the accepted C-to-Malbolge surface without forking Clang.

## Provenance

Official clang-tidy documentation describes the tool as an extensible framework
for diagnostics and fixes. Official contributing documentation explicitly
describes out-of-tree check plugins as shared libraries outside the clang-tidy
build system.

## Identity And Version

- Canonical name: clang-tidy
- Subject class: Static analysis and lint framework
- Stable identifier: LLVM Extra Clang Tools clang-tidy
- Publisher or authority: LLVM Project

## License Or Terms

This is external material. Citation does not relicense the source or import its
terms into the repository MIT license.

## Evidence

### Verified

- clang-tidy is based on Clang/LibTooling.
- Checks are modular and selectable by check-name patterns.
- Out-of-tree check plugins are supported as shared libraries.
- Out-of-tree plugin code must account for Clang API/version compatibility.

### Unresolved

The exact plugin ABI and build contract must be verified against the pinned LLVM
revision before the repository declares a supported plugin version.

## Sources

- <https://clang.llvm.org/extra/clang-tidy/index.html> - accessed 2026-07-26.
- <https://clang.llvm.org/extra/clang-tidy/Contributing.html> - accessed
  2026-07-26.
