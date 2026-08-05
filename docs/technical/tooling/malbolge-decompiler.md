# Malbolge decompiler and reverse engineering

## Status

Active implementation

## Purpose

Provide a profile-explicit reverse-engineering tool for valid Malbolge
artifacts.
The tool makes hostile self-modifying programs easier to inspect without
claiming
that compilation is mathematically reversible or that original C source can be
recovered from arbitrary Malbolge.

## Scope

- `tools/decompile/`
- `src/tooling/decompiler/composition/malbolge_decompile.rs`
- `src/tooling/decompiler/composition/museum_convert.rs`
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
silently replacing an earlier semantic choice:

```text
cargo run --bin malbolge_decompile -- \
  --profile malbolge-1998 \
  --representation c input.malbolge \
  --output output.c
```

`c` is the first representation, not the definition of decompilation. Future
reverse-engineering IR, control-flow/state annotations, mutation-history views,
or other readable forms remain open.

`museum_convert` is a separate tiny policy layer. It consumes one local file,
selects only frozen `malbolge-1998`, and writes a local C view through the same
general renderer. It performs no acquisition and adds nothing to the committed
museum.

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
current cell. Museum conversion never downloads a missing specimen or
substitutes another source.

## Verification

`tests/decompiler.rs` provides eight product tests covering deterministic
rendering, profile geometry, source rejection, post-jump encryption ordering,
output-capacity atomicity, normative
initial translation, and the interpreter-compatible `ubO`
input/output/halt baseline against `ProfileMachine`.

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
