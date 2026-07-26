# Deterministic C Surface And Clang Tooling

## Status

Accepted.

## Decision ID

`jig.malbolge.technical.deterministic-c-surface-and-clang-tooling`

## Context

Human-authored applications need a practical source language, while direct
Malbolge authoring is intentionally hostile. C provides a compact systems
surface but unrestricted C contains undefined, implementation-defined, and
host-specific behavior that cannot be lowered deterministically.

## Decision

C is the primary human-authored application language.

Pinned Clang parsing, preprocessing, type information, and AST tooling define
the frontend evidence used by `c2malbolge` and `malbolge-tidy`. The accepted C
surface is a deterministic profile with an explicit ABI and supported guest libc
contract.

`malbolge-tidy` is an out-of-tree clang-tidy plugin, not a fork. Its clean
verdict for a declared target profile means the compiler promises to lower the
program. A clean program rejected later as unsupported is a tooling bug.

AST-aware transformations own semantic rewrites. Regex is permitted only when a
change is proven purely textual.

## Advantages

- Makes the deterministic c surface and clang tooling boundary explicit,
  reviewable, and stable before implementation depends on it.

## Disadvantages

- The deterministic profile intentionally rejects some otherwise valid hosted C
  programs.

## Consequences

- Lowerability is a contract, not a best-effort compiler property.
- C diagnostics must distinguish forbidden semantics from capabilities that are
  merely not implemented yet.
- Compiler and tidy plugin share target-profile/ABI authority without sharing
  lowering implementation.

## Rejected Alternatives

### Rust as the user source language

Rejected because Rust is an implementation language for trusted tooling, not the
intended public application source surface.

### Unrestricted hosted C

Rejected because host ABI, undefined behavior, arbitrary platform APIs, and
implementation-defined types would make reproducible Malbolge semantics
impossible.

### Fork clang-tidy

Rejected because maintaining a Clang fork adds unnecessary toolchain ownership
and makes version drift harder to reason about.

## Evidence

- [ISO/IEC C language bibliography record](../../bibliography/languages/c.md)
- `docs/bibliography/platforms-and-runtimes/compiler/clang-libtooling.md`
- [clang-tidy bibliography record](../../bibliography/tooling/clang-tidy.md)

The plugin is pinned to the same LLVM revision used by frontend tooling. Profile
options must be deterministic and suitable for command-line and Jig invocation.
