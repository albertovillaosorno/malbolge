# Native Analysis

## Purpose

Native-analysis configuration contracts.

## Ownership

This boundary is owned by `function:native-analysis`.

## Prohibitions

It must not bypass another function or architectural kind boundary.

## Navigation

- [`contract/reference.md`](contract/reference.md): detailed
  pre-migration reference.
- `contract/`: pinned profile and LLVM toolchain identities.
- `adapter-inbound/`: out-of-tree clang-tidy check registration.
- `composition/`: project-owned clang-tidy host wiring.
- [CMake build entrypoint][tidy-cmake]: native build projection; implementation
  remains in this function.

[tidy-cmake]: ../../../tools/tidy/composition/CMakeLists.txt
