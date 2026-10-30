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

All four modes accept exactly one no-argument, non-variadic, void-return
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

A fourth opt-in `compile_canonical_typed_zero_prefixed_latest_byte_trace`
composes **initial zero outputs followed by the latest successful input**
without any host guest-byte emulation. It accepts exactly one canonical
`u8 ConstantInteger(0)` SSA definition, one or more outputs of that exact
zero SSA before the first `ByteInput`, one or more successful byte inputs,
and at least one output of the most recent input's SSA. Later reads
replace the accumulator; no zero SSA or older input SSA can be replayed
then. It admits exactly one void, no-argument function and one block,
retaining every instruction/source span and source/ABI/target identity
through independent canonical MCTR re-decoding and target layout.
All I/O operations run inside the selected normative VM; successful I/O
and unobserved return/ABI remain the declared limits. Maximum source is
4096 code cells, excluding the zero materialization already proven by
initial A=0. Nonzero/extra scalar definitions and unsupported operations
fail closed; all earlier adapter modes retain their original domains.

For input-based modes the equivalence claim requires successful byte
reads and writes with an ignored void ABI. Initial-zero output consumes no
input, but its guest writes must still succeed. None of the four modes
implements EOF, failed I/O, arithmetic, control flow or C source parsing.
The typed source digest remains copied provenance, not authentication of
external files.

### Canonical signed/unsigned byte-bitcast trace

The fifth byte-trace adapter mode
`compile_canonical_typed_identity_byte_trace` accepts exactly one
no-argument void-return canonical MCTI function with one phi-free block.
It admits `ByteInput`, `ByteOutput` and exact eight-bit `IntegerBitcast`
instructions between canonical `i8` and `u8`. Only aliases of the latest
successful input remain executable in the machine accumulator. The
source/SSA spans, source digest, ABI and profile identity survive ternary
lowering, canonical MCTR re-admission and independent target encoding.

The explicit CLI mode `--identity-byte-trace` accepts bounded MCTI/MCTR
through `--typed-file`, `--ternary-file`, `--typed-stdin`, or
`--ternary-stdin`. It proves exact byte I/O under two normative VM input
patterns, compares the independently re-encoded typed and ternary sources,
and uses existing atomic raw/capsule no-clobber publication. In particular,
a signed-byte alias is *not* a successful `u8` output until it has been
bitcast back; old zero-only, adjacent-echo and latest-read modes do not
admit casts. No host callback, EOF, arithmetic, byte register file,
branching or guest return ABI is implemented by this slice.

### Canonical one- or two-output nonzero literal

The separate `compile_canonical_typed_rotated_byte_literal` accepts a
canonical MCTI `u8 ConstantInteger`, one or two same-SSA `ByteOutput`s,
and `ReturnVoid` in a single no-argument void function. It preserves
source, SSA, ABI, profile and span identity through canonical MCTR and a
verified position-sensitive graphical source. The guest computes its `u8`
through genuine `j` data relocation and `*` rotation, not a host callback.
Fourteen current-profile nonzero values have one-output witnesses; ten
*different* values have exact two-output witnesses. The second `<` changes
the full loader-expanded memory, so old seeds cannot be reused. Each candidate
is re-executed before admission. Other values and output counts reject.
The opt-in CLI `--seeded-byte-literal` supports MCTI/MCTR file or bounded
stdin with raw/capsule no-clobber publication. EOF, general arithmetic,
arbitrary output sequences and guest ABI remain unimplemented.

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

For mixed initial-zero/latest-byte traces, use the independent opt-in
`--zero-prefixed-byte-trace --typed-file PATH` or
`--zero-prefixed-byte-trace --ternary-file PATH` CLI input. Their
`--typed-stdin` and `--ternary-stdin` analogues accept bounded canonical
wire streams; both
rejoin the independently admitted MCTR and normative VM preflight.
The publisher checks two fixed full-byte input patterns and expects leading
literal zero outputs, then outputs of only the latest successful read,
matching output and consumed-input count exactly. A source that reuses the
initial constant after a read cannot publish. Raw/capsule framing and atomic
no-clobber semantics are shared; the flag cannot mix with other modes.
A real split-wire regression checks that neither MCTI nor MCTR can publish
before EOF, even after its producer has sent the complete canonical bytes.

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
