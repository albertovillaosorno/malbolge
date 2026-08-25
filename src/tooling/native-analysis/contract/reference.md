# tools/tidy

`tools/tidy` defines the executable compatibility boundary for C that is
intended to be lowered to Malbolge. It is not the repository-wide C style or
native-code policy.

## Manual validation only

Guest-C validation is deliberately opt-in. The repository does not infer guest
status from the `.c` extension, general directory ownership, a magic source
comment, or an exclusion list. Native/reference C such as the VM oracle,
conformance
harnesses, historical sources, host tooling, and raw interoperability inputs are
therefore never constrained merely because they are C.

From the repository root, name every candidate translation unit explicitly:

```text
python src/automation/repository/composition/scripts/validate/main.py \
  path/to/program.c
```

Several explicitly selected units may be checked in one invocation:

```text
python src/automation/repository/composition/scripts/validate/main.py \
  first.c second.c
```

The one directory exception is an explicitly passed directory whose basename is
`doom` (case-insensitive). That directory is recursively expanded to its `.c`
translation units in deterministic path order:

```text
python src/automation/repository/composition/scripts/validate/main.py \
  path/to/doom
```

Other directories are rejected. This special case exists because DOOM is a
deliberate whole-program compatibility workload; it does not turn directory
discovery into general repository policy. Selection therefore remains an
explicit caller decision and cannot contaminate unrelated C/C++ validation.

`src/automation/repository/composition/scripts/validate/main.py` first validates
the canonical `malbolge-c32-v1` and `malbolge-libc-v1` authorities. It then runs
ABI and libc source preflights with repository-pinned Clang 22.1.8 and the
canonical `wasm32-unknown-unknown` frontend projection. Only sources admitted by
both contracts proceed to the LLVM 22.1.8 clang-tidy profile in
`src/tooling/native-analysis/contract/malbolge-clang-tidy.yaml`. When the
canonical project host and DLL are both present, the validator pairs them
automatically, verifies the DLL's exact registered `malbolge-*` set, and appends
those checks to the stock profile.

The wasm target is a checked parsing/data-layout projection, not the guest
backend. Native triples, native pointer widths, and non-default Clang address
spaces are not guest ABI authority.
Both the ABI Clang parser and the clang-tidy executable must report the pinned
LLVM 22.1.8 version. Alternate executable paths are useful for controlled
testing only when they preserve that version boundary; an arbitrary host LLVM
installation is rejected before source validation. The validator also supplies

the pinned LLVM 22 Clang resource directory explicitly.

## Pinned plugin build

The Windows plugin build is bound to the tracked
`llvm-clang-tidy-toolchain.json` identity. The exact development archive is
`clang+llvm-22.1.8-x86_64-pc-windows-msvc.tar.xz`, with size `862053924` bytes
and SHA-256
`d96c2cc1736f4eb7fa43cb9bbdf56d93551a9ae0a9aadb9c99c3c3b2b712a234`.
The repository does not download this artifact from validation code.

The reviewed archive supplies the clang-tidy C++ headers, static libraries, and
CMake metadata under `.dependencies/llvm-dev/22.1.8`. Build it with:

```text
python -m scripts.validate.tidy_build
```

On Windows, the official release `clang-tidy.exe` does not export the registry
symbol needed to share an out-of-tree DLL module. The project therefore relinks
the unmodified LLVM 22.1.8 `clangTidyMain` libraries into
`malbolge-clang-tidy.exe` and exports one bridge,
`malbolge_tidy_register_node`. The DLL still loads through the ordinary
clang-tidy `--load` option.

The current plugin registers five reviewed checks: bit-field, packed-layout,
pragma-pack, over-alignment, and type-surface checks. Together they emit the
closed `MALBOLGE-ABI-001` through `MALBOLGE-ABI-008` diagnostic set for every
`malbolge-c32-v1` source exclusion. The Python ABI preflight independently
enforces the same closed boundary before clang-tidy runs.

## What the profile means

A clean **current manual bootstrap** verdict means the selected translation
unit passed the canonical ABI and libc preflights plus the declared stock Clang
syntax and analyzer envelope. It does **not** yet promise complete Malbolge
lowerability.

Once the project-owned plugin and compiler contract are complete, a clean final
`tools/tidy` verdict means that the selected translation unit is inside the
declared deterministic guest-C profile and the compiler promises to lower it
for that target profile. That final statement is intentionally stronger than
ordinary code quality.

Later lowerability work may partition additional compatibility diagnostics into
these families:

- `malbolge-language-*`: C constructs outside the admitted guest language;
- `malbolge-abi-*`: representations or operations outside the declared ABI;
- `malbolge-runtime-*`: unavailable libc, OS, threading, or host facilities;
- `malbolge-determinism-*`: undefined, implementation-defined, or host-dependent
  behavior that cannot receive deterministic guest semantics;
- `malbolge-resource-*`: statically provable target-resource requirements that
  the declared profile cannot satisfy.

The checked language is intentionally much narrower than arbitrary hosted C.
In particular, the compatibility boundary is allowed to reject concurrency,
host I/O, OS APIs, implementation-dependent behavior, and other constructs that
cannot be given the target's sequential deterministic semantics. Exact
restrictions belong to the versioned target profile and the `malbolge-*` plugin
checks rather than ad-hoc source annotations.

`malbolge-clang-tidy.yaml` remains the stock executable bootstrap envelope. It
uses selected Clang diagnostics and analyzer checks, freestanding C23 parsing,
and hard warnings. The canonical plugin adds its reviewed checks without
removing that baseline.
The wrapper owns the closed target ABI, libc availability policy, and their
source-located preflights. The current lane-7 plugin still does not prove the

complete C-to-Malbolge contract. Semantic lowerability and executable guest
runtime
facilities, determinism, and resource proofs remain later project-owned work.

## Role of Rust tests

Rust tests are not the user-facing validator and do not decide which repository
files are guest C. They exist to develop and regress the profile itself:

```text
tests/tidy/accepted/*.c  -> tools/tidy must accept
tests/tidy/rejected/*.c  -> tools/tidy must reject with the expected family
```

As the compiler becomes available, accepted fixtures also exercise the stronger
contract:

```text
accepted C -> tools/tidy clean -> c2malbolge succeeds
```

A linter-clean supported program that the compiler later rejects is a
compiler/tooling contract regression.

## Current Malbolge and the 1998 conformance profile

The guest-C profile follows defined, reproducible interpreter semantics but
must not inherit undefined behavior, locale dependence, or accidental host-C
limits from Ben Olmstead's historical implementation.

`malbolge-1998` remains a frozen conformance profile for defined original
interpreter semantics, including ten-trit words and 59,049-word memory. Current
Malbolge is
a versioned evolution of the same language rather than a separately branded
"extended" dialect. It may remove historical resource ceilings while preserving
Malbolge's defining ternary arithmetic, crazy operation, rotate,
self-modification, post-encryption, sequential execution, and deterministic
semantics.

`tools/tidy` therefore validates against an explicit target profile. A program
may be valid current Malbolge C while exceeding `malbolge-1998` capacity;
that is
a profile requirement, not a generic C error. No profile inherits Ben
interpreter bugs or undocumented host behavior.
