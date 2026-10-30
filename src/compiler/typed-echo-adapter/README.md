# Typed Echo Adapter

## Purpose

Close executable typed-IR-to-ternary byte-I/O compiler gaps without relying
on a caller-manufactured semantic projection. The entrypoint accepts canonical
`malbolge-typed-ir-v1` bytes, verifies exact syntax and admitted typed IR,
projects the complete source function/effect trace, and lowers to canonical
`malbolge-ternary-ir-v1` (`MCTR`) bytes. It then separately decodes those
bytes, compares complete stage state, and passes the admitted result through
the existing independently verified Malbolge byte-echo layout backend.

## Supported domain

All three modes accept exactly one no-argument, non-variadic, void-return
function;
one entry block without phi nodes; and no globals or proof obligations.
`compile_canonical_typed_echo` preserves the original strict contract: one
or more adjacent successful typed-`u8` `ByteInput`/`ByteOutput` pairs using
the identical SSA ID. At most 2047 pairs fit its 4095-cell direct source.

`compile_canonical_typed_latest_byte_trace` is an explicit opt-in superset:
one or more successful byte inputs with zero or more outputs, each using
**only the most recent input's** exact SSA ID. A byte may be replayed many
times or consumed without output. A later read overwrites the VM accumulator;
replaying an older (but still valid typed-IR) SSA byte would require guest
memory and is rejected. The maximum verified layout has 4096 code
cells. Function, source
ID/digest, ABI, profile, return and operation spans all originate from the
validated upstream module. Unsupported shapes reject before any source
emission. This bridge does not perform I/O on the host.

A third, separately opt-in entrypoint,
`compile_canonical_typed_initial_zero_outputs`, accepts exactly one `u8`
`ConstantInteger(0)` SSA definition followed by one or more `ByteOutput`
instructions referring to that same SSA ID. It projects the real typed source
spans and exact constant bits into canonical MCTR, re-decodes that wire and
calls the independently verified `encode_initial_zero_outputs` target bridge.
The normative VM initializes its accumulator to zero, so every emitted
`OutputByte` executes on the guest without consuming any input. The target
contains only `OutputByte` instructions and a final `Halt`, while the
source-constant's provenance remains in the ternary IR. A maximum of 4095
outputs fits the 4096-cell code bound. Nonzero or additional constants,
other instructions, stale SSA, profile drift, and empty output traces reject.
Neither the original adjacent-echo API nor latest-read API is broadened.

For input-based modes the equivalence claim requires successful byte
reads and writes with an ignored void ABI. Initial-zero output consumes no
input, but its guest writes must still succeed. None of the three modes
implements EOF, failed I/O, arithmetic, control flow or C source parsing.
The typed source digest remains copied provenance, not authentication of
external files.

## Validation

```sh
cargo test --locked --test typed_echo_adapter --quiet
cargo clippy --locked --test typed_echo_adapter -- -D warnings
```

The integration suite checks independently restored typed/MCTR state and
real `ProfileMachine` output across multiple trace sizes. It also covers
the all-byte domain, exact 4096-cell upper bound, stale SSA rejection and
byte-identical old/new output for ordinary echo traces.

The `malbolge_layout` publisher now accepts canonical typed modules directly:

```sh
cargo run --bin malbolge_layout -- \
  --profile malbolge-2026 --output .temp/typed-echo.malbolge \
  --capsule -- --typed-file .temp/typed-echo.mcti
```

`--typed-file` defaults to strict adjacent echo. For latest-read traces use
`--latest-byte-trace --typed-file .temp/latest-read.mcti`. Both direct paths
internally re-decode the adapter's canonical MCTR output and re-encode its
position-sensitive Malbolge source with the *independent ternary bridge*,
requiring byte-identical source, exact profile fingerprint and code witness
length. The same normative VM successful-byte patterns and raw/capsule
no-clobber publication are retained. The integration regressions compare
both direct paths byte-for-byte against the older explicit MCTR workflow and
reject malformed, wrong-profile, stale-SSA and oversized MCTI without
creating a target. A direct MCTI-to-capsule-to-real-general-CLI regression
additionally feeds three binary guest bytes (including 0 and 255) and
requires the expected repeated latest-byte output; grammar errors and
trailing mixed-mode operands fail closed.

For the initial-zero-only subset, use the separate
`--initial-zero-output --typed-file PATH` or
`--initial-zero-output --ternary-file PATH` forms. The same options also
accept `--typed-stdin` and `--ternary-stdin` for a bounded canonical wire
producer. Each source enters the existing independently re-decoded MCTR,
position-sensitive target verification, exact no-input/extra-input normative
VM output-and-consumption preflight and no-overwrite raw/capsule publisher.
The explicit mode is incompatible with `--latest-byte-trace`; the default
commands remain strict adjacent byte echo. A real-process fragmented-wire
test verifies neither MCTI nor MCTR zero-output stdin may publish before
EOF, even after receiving the complete canonical byte sequence. Canonical
source files and pipes are compiler inputs, not guest stdin. This still
does not implement C input, nonzero output or a callable C guest ABI.

Canonical MCTI wire version one is intentionally pinned to `malbolge-2026`
and `malbolge-c32-v1`: unlike the lower-level VM and standalone layout
encoder, this typed compiler stage does **not** admit historical or immutable
versioned profile identities. The adapter now rejects a selected-profile
drift immediately after full canonical typed admission, before source
effect projection or ternary lowering. A real file-publisher regression
checks both strict and latest-read current-profile capsules through the
normative VM and actual binary-stdin runner, and rejects all four other
registered profile selectors without publishing. Another regression
publishes the entire 4096-cell latest-read trace (one read, 4094 outputs),
checks exact `0xff` guest output and consumption, and refuses 4097 cells.
This does not generalize the typed ABI or imply EOF semantics.

For the original strict echo subset, canonical `MCTR` bytes remain consumable
by the default `malbolge_layout --ternary-file` CLI. Its separate opt-in
`--latest-byte-trace --ternary-file` path now accepts the latest-successful-read
subset, preserving the same real VM preflight and no-clobber raw/capsule
publisher. The typed-adapter test exercises full canonical MCTI-to-MCTR-to-
published-capsule provenance, reloading the independent normative VM and
checking repeated output and unused consumed input. The strict default still
rejects this nonadjacent trace. Neither path realizes EOF, failed I/O, guest
byte storage, arbitrary C operations, source authentication or guest ABI.
