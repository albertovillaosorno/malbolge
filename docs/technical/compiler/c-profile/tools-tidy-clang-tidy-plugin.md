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
Runtime toolchain readiness and Linux import reuse additionally require the
exact LLVM version **and host-platform** bytes in the physical completion
marker, plus non-redirected native Clang/clang-tidy/clang-format executables,
neutral aliases, and (on Linux) both runtime shared libraries and the Clang
resource directory. The marker is compared using a bounded nonblocking
regular-file snapshot with inode and timestamp stability checks. Symlinks,
missing binaries, forged markers, and stale imports cannot count as ready or
be silently reused; an incomplete preexisting root fails closed.
The Linux importer also rejects linked host tool binaries and symlink/junction
members within the Clang resource tree, checking resource membership both
before and after staging. Windows neutral alias publication requires a physical
bundle and alias directory; existing aliases are checked against the exact
native PE bytes before any missing aliases or completion marker are written.
Linked and drifted aliases fail closed, while unchanged aliases remain reusable.

`tidy_toolchain.py` closes the manifest schema, rejects escaping paths and
host-dependent backslash separators, verifies required runtime/development
files with exact native status and physical unlinked regular-file admission,
checks the exact Clang and clang-tidy versions, and can hash an
explicitly supplied development archive. Manifest loading requires a bounded,
non-redirected regular file; the descriptor and pathname must retain inode,
extent, and timestamps throughout the read before
JSON parsing. Archive verification similarly hashes through a regular-file
descriptor (no-follow opening where supported) and rejects source replacement
or modification during streaming. Neither check accepts linked evidence paths
or treats a matching hash as permission to replace inputs. A failed source
stream wrapper or descriptor-identity preflight closes the owned descriptor
and reports a typed toolchain error with the underlying host failure as cause.
Native source errors retain their diagnostic text; foreign host exceptions use
their type name rather than executing custom string-formatting hooks. Source
admission requires exact native stat receipts, exact boolean symlink and
junction decisions for the leaf and all parents, nonnegative native `os.open`
descriptors, and exact native read bytes before inspecting lengths or hashes.
Clang and clang-tidy version probes likewise require native subprocess results,
exact command arguments, integer exit statuses, and native decoded
stdout/stderr; booleans, floats, foreign objects, and malformed host receipts
cannot prove a ready toolchain.
Version probes have a 15-second execution bound; timeouts preserve their
original host exception as the typed error cause without invoking foreign
exception formatters. Source stream ownership transfers
only to a native binary buffer wrapper; a foreign `fdopen` result is rejected
without reading its fields or leaking the opened descriptor. Manifest decoding,
source inspection, and archive hashing preserve the original host or UTF-8
failure as the typed error cause. Native error text is retained; foreign
exception formatters are never consulted. The toolchain CLI similarly prints
exact local `ToolchainError` messages but only the exception class name for
untrusted subclasses, avoiding their custom formatting hooks. CLI readiness
and argparse help require an exact native text-write count and completed
flush; short, boolean, foreign, or failed output receipts cannot report
success. Failed diagnostic delivery retains a nonzero validator status.

Linux LLVM development RPM publication also requires a physical, unlinked
completion marker and physical regular required headers under the tracked
repository-local development root. Marker content is compared to the exact
expected identity using a bounded, nonblocking descriptor read with inode,
size, and timestamp checks before and after. A symlinked root, redirected
include ancestor, altered marker, or incomplete extraction is not admitted as
ready; an existing incomplete root must be repaired explicitly rather than
silently using ambient headers or repeating a network download.
Readiness checks admit only exact native symlink/junction decisions and
regular-file stat results with bounded integer modes for the completion marker,
required headers, and their physical ancestors. False-like foreign statuses or
duck-typed stat objects cannot certify a reusable development root.
Before staging writes or destination publication, directory and leaf preflights
also require native boolean symlink, junction, existence, and directory status.
Malformed status results fail closed; host status exceptions retain their
original causes as typed provisioning errors without foreign formatter calls.
RPM extraction invokes `rpm2cpio` and CPIO only with separate expected and
launched command arguments. A successful tool receipt must be a native
`CompletedProcess` with the exact argument vector, integer exit status, and
binary stdout/stderr. In-place command mutation, foreign status or stream
objects, and malformed receipts fail closed; launch failures preserve their
original cause as a typed provisioning error without formatting foreign host
exception subclasses. Staged RPM and completion-marker writes additionally
require a previously unused, unlinked physical file path with nonredirected
parent directories. Existing regular files, symlinks, hardlinks, and nonnative
host status cannot be overwritten through the staging writer. RPM and marker
bytes use an exclusive no-follow create, a native regular-file descriptor
matched to the new leaf, and an exact native write count. An inserted
symlink or hardlink leaf cannot redirect a write after preflight. Publication
also admits each required extracted header through the physical regular-file
check used for readiness: linked header leaves, redirected ancestors,
missing files, and forged `is_file` results cannot complete an extracted
development kit.
CPIO extraction also admits only a physical `/usr/include` root and native
symlink/junction decisions for each enumerated include member. Linked include
roots, junctions, and false-like foreign path status cannot authorize copying
package headers outside the staging trust boundary. Pinned RPM download
reads are bounded to the declared package size plus one byte, with a 128 MiB
absolute ceiling. Oversized responses fail before hashing or extraction, and
admission requires an exact native byte response before size and SHA-256
verification. Network and response-read faults become typed provisioning
errors that retain native causes, without invoking foreign host exception
formatters. All package byte-verification entrypoints also require exact native
`bytes` before checking the pinned size and SHA-256, including when a custom
downloader is injected; bytearrays and byte subclasses cannot authorize RPM
extraction or publication.

The Linux plugin CMake builder likewise converts native process launch faults
into typed build failures with their original causes. Host diagnostics are
rendered only for exact built-in exception types; custom host exception text
hooks are not executed. Native CMake process receipts require the exact
invoked argument vector, integer exit status, and native stdout/stderr text;
foreign objects, substituted argv, and boolean or floating success values
cannot prove a successful configure/build command. Before each native build
phase, Linux output directories require exact boolean path-status evidence
and native physical `lstat` directory modes for each existing ancestor.
Contradictory path predicates, foreign stat receipts, linked ancestors, and
hostile error-formatting hooks fail closed. These non-atomic pathname checks
still cannot prevent concurrent replacement after a completed preflight.

### Windows plugin host

The Windows native plugin dispatcher authenticates every launched process
receipt before using its outputs or exit status. The exact native
`CompletedProcess` must name the requested list of string arguments and an
integer return code. Captured version, discovery, export, and check-list
commands must return native text streams; uncaptured build commands must not
report fabricated output streams. Missing or foreign receipts fail closed,
and native launch faults retain their original exception cause. Foreign host
exceptions and CLI errors are identified by type without evaluating custom
string-formatting hooks. The plugin builder CLI only reports success after
an exact native text-write count and completed flush. Short or foreign output
receipts and stdout failures cannot prove a ready plugin, while stderr failure
cannot turn invalid native build evidence into a successful command exit. This
subprocess admission does not provide an atomic lock against concurrent changes
to executable paths.

Windows cache, plugin-output, and tool parent paths also require native
boolean status and exact physical `lstat` directory-mode evidence on every
existing ancestor. Pinned tool and plugin files must have native regular-file
modes and must not redirect. Existing `build.cmd` files additionally require a
native single-link count before they may be overwritten; an exact missing
script path remains valid for initial creation. Contradictory or foreign
status/stat receipts fail closed. These checks also remain non-atomic with
respect to concurrent pathname replacement.

LLVM documents out-of-tree clang-tidy checks as shared-library plugins loaded
with `--load`, while also warning that plugin API/ABI compatibility is tied to
the exact clang-tidy build. Native guest-C validation subprocess probes
(Clang version, plugin registration, and analysis execution) normalize host
errors to typed configuration failures without invoking foreign exception
formatters, retaining the original host error as the cause. Tool, profile,
and plugin-file admission and implicit default host/plugin selection also
require exact native boolean regular-file verdicts before using filesystem
evidence, never foreign truthiness. Tool, profile, and implicit plugin path
resolution also require the exact native path type before comparisons or file
checks; foreign host path hooks cannot select an executable or plugin.
Read-only Clang version and plugin check-list
queries each have a 15-second execution bound; timeout exceptions become typed
configuration failures with their original causes. The official LLVM
22.1.8 Windows release layout has
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
stay under `.dependencies/tools-tidy/22.1.8/`. On Linux, CMake build-cache
and plugin-output paths must have physical directory ancestry; symlinks,
junctions, conflicting native status receipts, and non-directory substitutions
fail before native commands. Those paths are rechecked between configure and
build. The preflights do not make concurrent pathname replacement atomic.
Both Windows and Linux native build subprocess checks retain expected CMake/Ninja
arguments separately from the launched list. In-place mutation of subprocess
arguments cannot rewrite the expected command or certify a forged receipt.

On Windows, the generated `build.cmd` and its CMake cache require physical
unlinked directory ancestry; an existing linked or hardlinked build script is
rejected before its bytes can be overwritten. Clang resource publication also
rejects linked source tree members and redirected or non-directory destination
ancestors before deleting an old copy or installing a new one. These pathname
checks reduce accidental foreign writes but are not an atomic cross-process
publication lock.

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
Recursive `doom` selection rejects symlink and junction roots or discovered
entries before admitting the C units. Explicitly named single-file aliases
remain selectable. These admission checks do not freeze source bytes between
selection and the subsequent compiler execution.

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
