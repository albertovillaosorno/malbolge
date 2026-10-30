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

Both modes accept exactly one no-argument, non-variadic, void-return
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

The resulting native Malbolge program is semantically equivalent only on
successful byte reads/writes with ignored void guest ABI. It does not handle
EOF, failed I/O, arbitrary arithmetic, control flow or C source parsing.
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

For the original strict echo subset, canonical `MCTR` bytes remain consumable
by the default `malbolge_layout --ternary-file` CLI. Its separate opt-in
`--latest-byte-trace --ternary-file` path now accepts the latest-successful-read
subset, preserving the same real VM preflight and no-clobber raw/capsule
publisher. The typed-adapter test exercises full canonical MCTI-to-MCTR-to-
published-capsule provenance, reloading the independent normative VM and
checking repeated output and unused consumed input. The strict default still
rejects this nonadjacent trace. Neither path realizes EOF, failed I/O, guest
byte storage, arbitrary C operations, source authentication or guest ABI.
