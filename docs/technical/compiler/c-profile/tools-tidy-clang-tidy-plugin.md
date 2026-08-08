# tools/tidy clang-tidy plugin

## Status

Implemented for the lane-7 native-analysis boundary. Five reviewed plugin checks
enforce all closed `malbolge-c32-v1` source exclusions. Complete guest-C
lowerability remains a later contract.

## Purpose

Build `tools/tidy/` as an out-of-tree clang-tidy plugin compiled against exactly
LLVM 22.1.8. Add project-owned `malbolge-*` checks without forking Clang or
weakening the existing stock clang-tidy baseline.

## Scope

This document governs the following declared TODO scope:

- `tools/tidy/` as the repository-local native build entrypoint;
- `src/tooling/native-analysis/` as plugin and host implementation ownership;
- `src/automation/repository/composition/scripts/validate/` as build and manual
  validation orchestration;
- `tests/tidy/` plus Python regression evidence for the compatibility boundary;
- guest-C ABI, libc, and runtime contracts only where a check consumes their
  already-declared authority.

The full language, runtime, determinism, resource, and compiler-lowerability
proof is not owned by this lane-7 plugin bootstrap.

## Current Behavior

### Exact LLVM development identity

`src/tooling/native-analysis/contract/llvm-clang-tidy-toolchain.json` pins the
Windows x86-64 development artifact to:

- LLVM version `22.1.8` and release tag `llvmorg-22.1.8`;
- asset `clang+llvm-22.1.8-x86_64-pc-windows-msvc.tar.xz`;
- size `862053924` bytes;
- SHA-256
  `d96c2cc1736f4eb7fa43cb9bbdf56d93551a9ae0a9aadb9c99c3c3b2b712a234`.

The normal repository LLVM installation remains the runtime compiler/tool
package at `.dependencies/llvm/22.1.8`. Plugin construction additionally uses
headers, static libraries, CMake package metadata, and LLVM build tools
extracted
from the reviewed development artifact into `.dependencies/llvm-dev/22.1.8`.
Neither path is inferred from an ambient host LLVM installation.

`tidy_toolchain.py` closes the manifest schema, rejects escaping paths, verifies
required runtime/development files, checks the exact Clang and clang-tidy
versions, and can hash an explicitly supplied development archive.

### Windows plugin host

LLVM documents out-of-tree clang-tidy checks as shared-library plugins loaded
with `--load`, while also warning that plugin API/ABI compatibility is tied to
the exact clang-tidy build. The official LLVM 22.1.8 Windows release layout has
plugin symbol exporting disabled, so its prebuilt `clang-tidy.exe` does not
export the registry operation required by an out-of-tree DLL.

The project therefore relinks the unmodified LLVM 22.1.8 `clangTidyMain` static
libraries into `malbolge-clang-tidy.exe`. That host exports one project-owned C
bridge named `malbolge_tidy_register_node`. The out-of-tree DLL resolves only
that bridge from the host process and supplies its
`ClangTidyModuleRegistry::node`. No Clang source fork is maintained.

This bridge is deliberately narrow. The plugin and host still compile against
the exact same LLVM 22.1.8 C++ headers and static libraries. The bridge only
solves the Windows registry-sharing problem; it does not create a general
project ABI for arbitrary LLVM objects.

### Reproducible local build

`tidy_build.py` discovers a Visual Studio installation with the x64 VC toolset,
uses the Visual Studio CMake/Ninja distribution, and compiles with the pinned
LLVM `clang-cl.exe`. The generated build tree stays under `.cache/` and outputs
stay under `.dependencies/tools-tidy/22.1.8/`.

The LLVM development archive's exported `LLVMDebugInfoPDB` CMake target embeds a
DIA SDK path from the upstream build machine. The build entrypoint does not edit
the extracted LLVM package. It validates that the imported target still has the
expected DIA dependency and replaces only that dependency in memory with the
local Visual Studio Build Tools `diaguids.lib` path.

After compilation, the build helper verifies all of the following before it
reports success:

- the project host reports LLVM `22.1.8`;
- the host exports `malbolge_tidy_register_node`;
- the DLL loads through `--load`;
- the DLL registers the exact reviewed `malbolge-*` check set.

### Current plugin checks

The reviewed plugin check set is exactly:

- `malbolge-abi-bit-field`: `MALBOLGE-ABI-001` for bit-fields;
- `malbolge-abi-packed-layout`: `MALBOLGE-ABI-002` for packed records
  and packed fields;
- `malbolge-abi-pragma-pack`: `MALBOLGE-ABI-003` for `#pragma pack`;
- `malbolge-abi-over-alignment`: `MALBOLGE-ABI-004` for requested
  alignment above 16 bytes;
- `malbolge-abi-type-surface`: `MALBOLGE-ABI-005` through
  `MALBOLGE-ABI-008` for `_BitInt`, `__int128`, compiler vector types, and
  non-default address spaces.

The plugin uses Clang AST declarations and canonical types rather than host C
layout. Local typedef declarations own their diagnostic so later uses do not
duplicate it. A forbidden alias imported from a header is diagnosed when the
selected translation unit uses it, preserving a source-local compatibility
decision.

`c_abi_source.py` remains an independent ABI preflight over the same closed v1
exclusions. The duplicate enforcement is deliberate during compiler bring-up:
the AST JSON preflight protects the manual validator before clang-tidy runs,
while the DLL proves the out-of-tree tooling boundary can enforce the same ABI
contract without relying on Python as its final implementation.

### Manual guest-C validation

Guest-C enrollment remains explicit. The manual validator accepts named `.c`
translation units, plus one explicitly passed directory whose basename is
`doom`. It does not infer guest status from file extension, directory ownership,
source comments, or a repository-wide `.clang-tidy` file.

When the canonical project host and DLL are both present, `main.py` pairs them
automatically. An explicitly selected upstream `clang-tidy.exe` does not inherit
the project DLL. Whenever a plugin is selected, the validator first probes
registration with `--list-checks` and fails closed unless the loader exposes
exactly the reviewed `malbolge-*` set. This prevents the official Windows
`clang-tidy.exe` from silently accepting `--load` while failing to share the
plugin registry.

Plugin checks are appended to the existing stock profile and are also appended
to `WarningsAsErrors`. They never replace or subtract the stock analyzer/check
selection. The validator also supplies the pinned LLVM 22 Clang resource
directory explicitly with the selected frontend target.

## Invariants

- Host, plugin, frontend parser, and development kit are all LLVM `22.1.8`.
- The development archive identity is exact by release tag, size, and SHA-256.
- Plugin construction never mutates the extracted LLVM development package.
- The plugin is a DLL loaded with clang-tidy `--load`; it is not statically
  compiled into a maintained Clang fork.
- The Windows host exports only the reviewed registry bridge required to share
  module registration with the DLL.
- An explicitly supplied plugin must register exactly the documented
  `malbolge-*` checks before source validation starts.
- Plugin checks are additive to the ordinary clang-tidy profile and are hard
  errors when explicitly loaded.
- Guest-C validation remains manual and opt-in. Arbitrary repository C is never
  enrolled automatically.
- A clean lane-7 plugin verdict does not claim complete C-to-Malbolge
  lowerability. That stronger statement belongs to the later lowerability
  contract.

## Failure Behavior

Malformed or drifted toolchain manifests fail before native build execution.
Missing development headers/libraries, a wrong LLVM version, a wrong platform,
or an archive hash/size mismatch fail closed.

Missing Visual Studio VC tools, CMake/Ninja, the x64 DIA SDK library, or a
changed
LLVM imported-target shape stops the native build rather than falling back to an
ambient compiler or library.

A plugin that cannot load, registers no check, or registers an undocumented
`malbolge-*` check is rejected before guest source validation. Unsupported ABI
constructs are diagnosed at source locations with the closed
`MALBOLGE-ABI-001` through `MALBOLGE-ABI-008` diagnostic set.

## Verification

The durable regression surface includes:

- closed manifest and archive identity tests in `tests/test_tidy_toolchain.py`;
- real DLL registration tests against the canonical project host;
- both accepted ABI fixtures executing cleanly through the real DLL;
- the complete rejected ABI fixture corpus producing source-located
  `MALBOLGE-ABI-001` through `MALBOLGE-ABI-008` diagnostics;
- plugin-only imported-typedef evidence proving main-file source use is caught;
- Rust integration tests that regress registration and fixture behavior whenever
  the optional native outputs are locally provisioned;
- manual-validator tests proving plugin checks are additive and canonical host
  and DLL outputs are paired automatically;
- a negative loader test proving the upstream Windows executable cannot silently
  bypass the project registry bridge;
- existing deterministic ABI preflight tests in `tests/test_c_abi.py`.

Validate a previously downloaded archive with:

```text
python -m scripts.validate.tidy_toolchain --archive path/to/clang+llvm.tar.xz
```

Build and verify the native plugin outputs with:

```text
python -m scripts.validate.tidy_build
```

Run manual guest-C validation after building the canonical outputs with:

```text
python src/automation/repository/composition/scripts/validate/main.py \
  path/to/program.c
```

The validator selects the canonical project host and DLL together when both are
present. `--clang-tidy` and `--plugin` remain explicit test/debug overrides.

## References

- [Deterministic C Surface And Clang
  Tooling](../../adr/deterministic-c-surface-and-clang-tooling.md)
- [Compiler Pipeline And Guest
  Runtime](../../adr/compiler-pipeline-and-guest-runtime.md)
- [Clang-Tidy Extensible
  Checks](../../../bibliography/tooling/clang-tidy.md)
- [LLVM 22.1.8
  release](https://github.com/llvm/llvm-project/releases/tag/llvmorg-22.1.8)
- [clang-tidy contributing
  documentation](https://clang.llvm.org/extra/clang-tidy/Contributing.html)

### Governing ADR Paths

- `docs/technical/adr/deterministic-c-surface-and-clang-tooling.md`
- `docs/technical/adr/compiler-pipeline-and-guest-runtime.md`
