# LLVM Intermediate Representation

## Status

Verified; evidence verified.

## Subject

- Canonical name: LLVM Language Reference Manual
- Subject class: Compiler intermediate representation specification
- Stable identifier: LLVM Language Reference Manual
- Publisher or authority: LLVM Project

## Repository Use

LLVM IR is prior art for typed intermediate representation design, SSA-based
compiler pipelines, translation validation targets, and the distinction between
in-memory, serialized, and human-readable IR forms.

## Provenance

The official LLVM documentation is the primary source. The accessed live manual
identifies itself as LLVM 24.0.0git documentation; this record does not imply
that Malbolge adopts LLVM IR as its compiler IR.

## Identity And Version

- Canonical name: LLVM Language Reference Manual
- Subject class: Compiler intermediate representation specification
- Stable identifier: LLVM Language Reference Manual
- Publisher or authority: LLVM Project

## License Or Terms

This is external material. Citation does not relicense the source or import its
terms into the repository MIT license.

## Evidence

### Verified

- LLVM describes its IR as SSA-based and type-safe.
- The same code representation has in-memory, bitcode, and human-readable forms.
- The IR is intended to support compiler transformation and analysis across
  compilation phases.

### Unresolved

The Malbolge compiler intentionally seeks a smaller deterministic IR. Which LLVM
ideas transfer cleanly is a project design question, not a fact established by
this source.

## Sources

- <https://llvm.org/docs/LangRef.html> - accessed 2026-07-26.
