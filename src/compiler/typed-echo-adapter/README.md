# Typed Echo Adapter

## Purpose

Close one executable typed-IR-to-ternary compiler gap without relying on a
caller-manufactured semantic projection. The entrypoint accepts canonical
`malbolge-typed-ir-v1` bytes, verifies exact syntax and admitted typed IR,
projects the complete source function/effect trace, and lowers to canonical
`malbolge-ternary-ir-v1` (`MCTR`) bytes. It then separately decodes those
bytes, compares complete stage state, and passes the admitted result through
the existing independently verified Malbolge byte-echo layout backend.

## Supported domain

Exactly one no-argument, non-variadic, void-return function; one entry block
with no phi nodes; no globals or proof obligations; and one or more adjacent
successful typed-`u8` `ByteInput`/`ByteOutput` pairs using identical SSA IDs.
At most 2047 pairs fit the bounded 4095-cell direct source. Function, source
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
real `ProfileMachine` output across multiple trace sizes. The result also
provides canonical `MCTR` bytes consumable by the existing
`malbolge_layout --ternary-file` publication CLI, which remains the sole
artifact publisher. No competing publication or partial target files are
introduced here.
