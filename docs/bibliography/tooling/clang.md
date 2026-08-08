# Clang 22.1.8

## Status

Verified; repository executable version and release-family documentation checked
on 2026-08-08.

## Subject

- Canonical name: Clang 22.1.8
- Subject class: C/C++ compiler frontend and driver
- Stable identifier: LLVM release `llvmorg-22.1.8`
- Publisher or authority: LLVM Project

## Repository Use

Clang 22.1.8 is the pinned parser and frontend evidence source for deterministic
guest C. It provides the checked wasm32 parsing projection, freestanding
compiler headers, AST JSON used by source preflights, and native test
compilation
without defining guest ABI or guest-library semantics.

## Provenance

The repository verifies the installed executable reports Clang 22.1.8. LLVM's
22.1 release-family command guide documents `-ffreestanding` and states that a
freestanding build still needs the applicable C library interfaces, including
`memcpy`, `memmove`, and `memset`.

LLVM's 22.1 language-extension documentation describes
`__builtin_memcpy_inline` and `__builtin_memset_inline` as building blocks for a
custom libc and guarantees those inline forms do not call external functions,
subject to their compile-time-size constraints.

## Identity And Version

- Canonical name: Clang 22.1.8
- Subject class: C/C++ compiler frontend and driver
- Stable identifier: LLVM release `llvmorg-22.1.8`
- Publisher or authority: LLVM Project

## License Or Terms

Clang is LLVM Project software distributed under Apache License 2.0 with LLVM
exceptions. Citing or executing it does not relicense guest source or repository
policy.

## Evidence

### Verified

- The repository-pinned frontend reports `clang version 22.1.8`.
- LLVM documents that `-ffreestanding` does not eliminate the need for required
  C library interfaces such as `memcpy`, `memmove`, and `memset`.
- LLVM documents guaranteed-inline memory builtins intended for custom libc
  implementations when their constraints are satisfied.
- The repository uses `-fno-builtin` while validating the executable v1 guest
  memory/string implementations so correctness does not depend on host builtins.

### Unresolved

Later optimization work may choose verified compiler intrinsics for individual
library routines, but each substitution must preserve the versioned
guest-visible
semantics and cannot create a host-library dependency.

## Sources

- <https://releases.llvm.org/22.1.0/tools/clang/docs/CommandGuide/clang.html> -
  accessed 2026-08-08.
- <https://releases.llvm.org/22.1.0/tools/clang/docs/LanguageExtensions.html> -
  accessed 2026-08-08.
- <https://github.com/llvm/llvm-project/releases/tag/llvmorg-22.1.8> - accessed
  2026-08-08.
