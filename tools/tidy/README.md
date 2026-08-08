# tidy Tool Function Boundary

## Purpose

This boundary owns the reproducible native build entrypoint for the project
clang-tidy host and out-of-tree plugin. The implementation itself remains in
the governed `src/tooling/native-analysis` function.

## Ownership

- Owns: Native build composition for the pinned clang-tidy extension artifacts.
- Authority: `tools/tidy/function.yml`.

## Prohibitions

- Must not: Own guest-C analysis semantics or duplicate native-analysis source.
- Must not: Discover ambient LLVM versions or bypass the tracked toolchain pin.

## Navigation

- `function.yml` declares the governed tool composition part.
- `composition/CMakeLists.txt` links the pinned project host and plugin outputs.
