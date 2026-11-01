# Malbolge decompiler and reverse engineering

## Status

Accepted implementation

## Purpose

Provide a profile-explicit reverse-engineering tool for valid Malbolge
artifacts.
The tool makes hostile self-modifying programs easier to inspect without
claiming
that compilation is mathematically reversible or that original C source can be
recovered from arbitrary Malbolge.

## Scope

- `src/tooling/decompiler/domain/analysis.rs`
- `src/tooling/decompiler/application/render.rs`
- `src/tooling/decompiler/composition/cli.rs`
- `src/tooling/decompiler/composition/malbolge_decompile.rs`
- `tests/decompiler.rs`
- local generated views of `examples/museum/` specimens

## Current Behavior

`src/tooling/decompiler/application/render.rs` emits C23 as a source-specialized
semantic machine.
Before rendering, the source is admitted by `ProfileMachine::from_source` for
the
explicit canonical profile. The generated artifact embeds exact profile ID,
version, fingerprint, word modulus, memory size, EOF value, trit width,
input/output instruction bytes, non-graphical progress policy, admitted source
bytes, and the normative initial translation table.

The generated C exposes explicit accumulator/code/data registers and uses
caller-owned memory, input, output, and result storage. It implements profile-
width crazy and rotate operations, position-dependent decode, bounded execution,
self-modification, post-instruction encryption, and explicit status values. It
deliberately calls no `malloc`, `getchar`, `putchar`, thread API, or platform
service.

The general Cargo entrypoint delegates policy to
`src/tooling/decompiler/application/cli.rs` and
requires both profile and output representation explicitly. Repeating
`--profile`, `--representation`, or `--output`/`-o` is rejected instead of
silently replacing an earlier semantic choice. Help is accepted only as the
sole argument, so it cannot hide malformed or contradictory input:

```text
cargo run --bin malbolge_decompile -- \
  --profile malbolge-1998 \
  --representation analysis \
  input.malbolge
```

`analysis` emits a typed initial-state report before execution mutates code or
pointers. It records raw/decoded cells, accumulator and data effects,
sequential/indirect/halt control-flow classes, and post-step encryption.
Indirect targets remain explicitly unresolved and the report states that
self-modification invalidates a purely static decode.

The `annotated` representation emits a profile-explicit, directly
canonicalizable Malbolge presentation instead of a separate report or C
translation. It retains every loaded byte verbatim and uses full-line `# `
comments for exact canonical position ranges and initial control-flow labels.
The view breaks after initially decoded indirect and halt cells and at most
64 bytes otherwise. The selected-profile loader still performs input admission;
consumers must explicitly choose the annotated frontend to strip comments.
After stripping those comments and presentation line breaks, the canonical
loaded positions, VM semantics, and emitted bytes are unchanged. An initial
indirect label does not recover its target or predict future self-modification.

`--source-format annotated` separately opts into the v1 comment-stripping
frontend for decompiler input; it works with `analysis`, `annotated`, and `c`
outputs. The default `raw` input format never strips comments, regardless of
file extension. In both cases, the exact selected-profile loader is final
source admission after the input file is read under the 1 MiB byte cap.
Malformed annotated presentation fails instead of falling back to raw.

```text
cargo run --bin malbolge_decompile -- \
  --profile malbolge-1998 --representation annotated \
  input.malbolge --output input.annotated.malbolge
```

Dynamic traces, mutation-history views, and deeper recovered structure are
optional extensions with separate ownership; they do not reopen this accepted
initial reverse-engineering boundary.

Historical museum conversion uses the same general CLI with the explicit frozen
`malbolge-1998` profile. No second executable root or implicit profile policy is
required:

```text
cargo run --bin malbolge_decompile -- \
  --profile malbolge-1998 \
  --representation c INPUT.malbolge \
  --output OUTPUT.c
```

The command performs no acquisition and adds nothing to the committed museum.

## Invariants

- The selected canonical target profile remains the semantic authority.
- Input must pass the canonical profile loader before any representation exists.
- The initial listing uses normative `XLAT1`; raw `(cell + C) mod 94` is only an
  index and is never treated as the decoded instruction itself.
- Executable representations preserve input/output order, crazy, rotate, jumps,
  the post-jump encryption target, pointer advancement/wrap, halt,
  profile-declared non-graphical behavior, EOF, and atomic rejection.
- Self-modification is represented as behavior, not optimized away to make the
  output look more conventional.
- Output capacity is consumed only when an instruction actually emits a byte;
  it is never inflated to the requested step budget. Exhaustion rejects the
  pending transition before output, encryption, register, or pointer mutation.
- `malbolge_decompiled_run` initializes caller-visible result storage
  deterministically even when arguments are rejected.
- Generated or museum-derived views do not become semantic or licensing
  authority merely because they are readable.

## Failure Behavior

Invalid Malbolge source fails before rendering through the selected profile's
loader diagnostics. Unknown profiles and unknown output representations fail
explicitly in the general CLI; there is no fallback.

Generated C returns explicit invalid-argument, invalid-encryption, and
output-exhausted statuses. A rejected encryption target or exhausted output
buffer commits no input, output, register, or memory transition for that step.
Halt and modern non-graphical termination are distinct outcomes;
`malbolge-1998` instead preserves bounded non-progress for a non-graphical
current cell. Historical conversion never downloads a missing specimen or
substitutes another source.

## Verification

`tests/decompiler.rs` includes product tests covering deterministic
rendering, profile geometry, source rejection, post-jump encryption ordering,
output-capacity atomicity, normative initial translation, typed initial-state
analysis, CLI analysis output, and the interpreter-compatible `ubO`
input/output/halt baseline against `ProfileMachine`, plus annotated
round trips, source-position mappings, initial-state structural boundaries,
historic/current VM equivalence, CLI stdout/file identity, and explicit
annotated input mode isolation against raw and malformed presentation.

Pinned LLVM 22.1.8 development evidence compiled generated historical `ubO` C
with `-std=c23 -ffreestanding -Wall -Wextra -Werror` for both
`x86_64-pc-windows-msvc` and `aarch64-pc-windows-msvc`. The x86-64 object linked
without the CRT and executed through its exported API. Input byte `0x41`
produced
exactly:

```text
status=halt
A=65 C=2 D=2
input_consumed=1
output="A"
steps=3
```

That native compile/run is implementation evidence, not an independent semantic
oracle. The interpreter-authority VM and declared target profile remain the
acceptance authority.

## References

- [Canonical target profile](../specification/target-profile.md)
- [Interpreter authority and Malbolge
  evolution](../adr/specification-authority-and-malbolge-evolution.md)
- [Verification trust boundary](../adr/verification-trust-boundary.md)
