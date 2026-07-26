# Clang-Tidy Extensible Checks

- Review status: Verified
- Evidence status: Verified
- As-of date: 2026-07-26

## Identity

- Canonical name: clang-tidy
- Subject class: Static analysis and lint framework
- Stable identifier: LLVM Extra Clang Tools clang-tidy
- Publisher or authority: LLVM Project

## Repository Relevance

`malbolge-tidy` is planned as an out-of-tree clang-tidy plugin that expresses
the accepted C-to-Malbolge surface without forking Clang.

## Source Quality And Provenance

Official clang-tidy documentation describes the tool as an extensible framework
for diagnostics and fixes. Official contributing documentation explicitly
describes out-of-tree check plugins as shared libraries outside the clang-tidy
build system.

## Verified Claims

- clang-tidy is based on Clang/LibTooling.
- Checks are modular and selectable by check-name patterns.
- Out-of-tree check plugins are supported as shared libraries.
- Out-of-tree plugin code must account for Clang API/version compatibility.

## Unresolved Evidence

The exact plugin ABI and build contract must be verified against the pinned LLVM
revision before the repository declares a supported plugin version.

## Sources

- <https://clang.llvm.org/extra/clang-tidy/index.html> - accessed 2026-07-26.
- <https://clang.llvm.org/extra/clang-tidy/Contributing.html> - accessed
  2026-07-26.
