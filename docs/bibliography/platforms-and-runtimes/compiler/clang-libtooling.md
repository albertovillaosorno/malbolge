# Clang LibTooling

## Status

Verified; evidence verified.

## Subject

- Canonical name: Clang LibTooling
- Subject class: C and C++ compiler tooling API
- Stable identifier: LLVM Clang LibTooling
- Publisher or authority: LLVM Project

## Repository Use

LibTooling is the implemented parser/AST foundation for the normalized guest-C
frontend and remains the AST-aware tooling foundation for transformations that
must not be implemented as unsafe textual concatenation. Product code is built
against exactly LLVM/Clang 22.1.8 and emits a repository-owned artifact rather
than serializing Clang AST objects or dump output.

## Provenance

Official Clang documentation is primary. The repository uses release-series
22.1 documentation together with the exact 22.1.8 development archive pinned by
native tooling. Current Clang source/documentation is supporting evidence for
why raw AST dump formats remain outside the durable compiler boundary.

## Identity And Version

- Canonical name: Clang LibTooling
- Subject class: C and C++ compiler tooling API
- Stable identifier: LLVM Clang LibTooling
- Publisher or authority: LLVM Project

## License Or Terms

This is external material. Citation does not relicense the source or import its
terms into the repository MIT license.

## Evidence

### Verified

- LibTooling supports standalone tools built on Clang.
- LibTooling tools run frontend actions over source code.
- Clang documents LibTooling as appropriate when a tool needs direct control
  over the Clang AST.
- Clang explicitly warns that this interface is not a stable API across
  versions.
- Clang documents parsing and semantic analysis as constructing the source-level
  AST before LLVM IR generation.
- Clang 22.1 release notes contain a dedicated AST-dumping potentially breaking
  changes section, so dump output is not treated as the repository artifact.
- The repository's exact 22.1.8 adapter uses frontend actions and AST traversal
  while normalizing identity, types, constants, references, and source spans.

### Unresolved

A future LLVM/Clang upgrade must be validated against the repository-owned
`malbolge-c-frontend-v1` artifact. No upstream C++ API/ABI stability is assumed.

## Sources

- <https://releases.llvm.org/22.1.0/tools/clang/docs/LibTooling.html> -
  accessed 2026-08-08.
- <https://releases.llvm.org/22.1.0/tools/clang/docs/Toolchain.html> - accessed
  2026-08-08.
- <https://releases.llvm.org/22.1.0/tools/clang/docs/ReleaseNotes.html> -
  accessed 2026-08-08.
- <https://clang.llvm.org/docs/LibTooling.html> - accessed 2026-08-08.
- <https://clang.llvm.org/doxygen/DumpAST_8h_source.html> - accessed 2026-08-08.
