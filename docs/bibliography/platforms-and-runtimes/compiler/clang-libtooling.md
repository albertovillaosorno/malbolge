# Clang LibTooling

## Status

Verified; evidence verified.

## Subject

- Canonical name: Clang LibTooling
- Subject class: C and C++ compiler tooling API
- Stable identifier: LLVM Clang LibTooling
- Publisher or authority: LLVM Project

## Repository Use

LibTooling is the planned parser/AST/tooling foundation for C frontend work and
for AST-aware interoperability transformations that must not be implemented as
unsafe textual concatenation.

## Provenance

The official Clang documentation is primary. The accessed documentation
identifies itself as Clang 24.0.0git documentation.

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

### Unresolved

Exact API calls and binary compatibility must be pinned to the repository's
selected LLVM revision when implementation begins.

## Sources

- <https://clang.llvm.org/docs/LibTooling.html> - accessed 2026-07-26.
- <https://clang.llvm.org/docs/Tooling.html> - accessed 2026-07-26.
