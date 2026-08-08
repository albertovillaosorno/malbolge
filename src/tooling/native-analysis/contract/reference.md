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
python src/automation/repository/composition/scripts/validate/main.py path/to/program.c
```

Several explicitly selected units may be checked in one invocation:

```text
python src/automation/repository/composition/scripts/validate/main.py first.c second.c
```

The one directory exception is an explicitly passed directory whose basename is
`doom` (case-insensitive). That directory is recursively expanded to its `.c`
translation units in deterministic path order:

```text
python src/automation/repository/composition/scripts/validate/main.py path/to/doom
```

Other directories are rejected. This special case exists because DOOM is a
deliberate whole-program compatibility workload; it does not turn directory
discovery into general repository policy. Selection therefore remains an
explicit caller decision and cannot contaminate unrelated C/C++ validation.

`src/automation/repository/composition/scripts/validate/main.py` first validates
the canonical `malbolge-c32-v1` authority, then runs the ABI-only source
preflight with repository-pinned Clang 22.1.8 and the canonical
`wasm32-unknown-unknown` frontend projection. Only ABI-admitted sources proceed
to the repository-pinned LLVM 22.1.8 clang-tidy bootstrap and
`src/tooling/native-analysis/contract/malbolge-clang-tidy.yaml`. Once the
out-of-tree plugin exists, pass its built shared library with `--plugin`; the
durable CLI may later hide that implementation detail.

The wasm target is a checked parsing/data-layout projection, not the guest
backend. Native triples, native pointer widths, and non-default Clang address
spaces are not guest ABI authority.
Both the ABI Clang parser and the clang-tidy executable must report the pinned
LLVM 22.1.8 version. Alternate executable paths are useful for controlled
testing only when they preserve that version boundary; an arbitrary host LLVM
installation is rejected before source validation.

## What the profile means

A clean **current manual bootstrap** verdict means the selected translation
unit passed the canonical ABI preflight plus the declared stock Clang syntax
and analyzer envelope. It does **not** yet promise complete Malbolge
lowerability.

Once the project-owned plugin and compiler contract are complete, a clean final
`tools/tidy` verdict means that the selected translation unit is inside the
declared deterministic guest-C profile and the compiler promises to lower it
for that target profile. That final statement is intentionally stronger than
ordinary code quality.

The final plugin partitions compatibility diagnostics into these families:

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

`malbolge-clang-tidy.yaml` is currently the stock executable bootstrap
envelope. It uses selected Clang diagnostics and analyzer checks, freestanding
C23 parsing, and hard warnings. The wrapper now owns the closed target ABI and
source-located `MALBOLGE-ABI-*` preflight, but stock clang-tidy still cannot
prove the complete C-to-Malbolge contract. Semantic lowerability, exact guest
libc/runtime availability, determinism, and resource proofs remain
project-owned `malbolge-*` plugin work.

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
may be valid current Malbolge C while exceeding `malbolge-1998` capacity; that is
a profile requirement, not a generic C error. No profile inherits Ben
interpreter bugs or undocumented host behavior.
