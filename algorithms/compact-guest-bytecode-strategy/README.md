# Compact guest bytecode strategy: echo macro pilot

## Boundary

This is a research-only structural-compression candidate, **not** a guest
bytecode interpreter and not a compiler backend. The `CEB1` descriptor is six
bytes: four literal magic/version bytes and a little-endian `u16` repetition
count. It describes exactly `n` consecutive successful `ByteInput`/`ByteOutput`
SSA-identical pairs followed by `ReturnVoid`, with `1 <= n <= 2047`.

Both encoding and independent admission require the original already-validated
canonical `malbolge-ternary-ir-v1` program and selected `malbolge-2026` profile.
The descriptor does **not** contain the original source identity, source digest,
ABI, profile fingerprint, function metadata, or guest data placement. Another
valid equal-length source can reuse the same candidate. It cannot be published
or executed as a stand-alone trusted artifact.

## Verification

The candidate generator checks the canonical ternary program and exact effect
shape. The independent decoder checks the full count and every source pair,
reconstructs a **direct** layout on the host, and asks the existing trusted
position-sensitive encoder to verify the final graphical source.

```sh
cargo test --locked --test compact_guest_bytecode_strategy --quiet
cargo clippy --locked --test compact_guest_bytecode_strategy -- -D warnings
```

The test runs all 256 successful `u8` input values through the normative VM
using **expanded direct source**, not guest-interpreted bytecode. Other cases
check 1, 2, 3, 7, 20, 64, 256, and 2047 echo pairs, including the 4095-cell
upper direct bound. The complete 4095-cell source also runs on the normative
VM with all 2047 effects observed in order. All single-byte substitutions,
truncations, trailing bytes, profile drift, wrong SSA uses, empty and overlarge
traces reject. A separate test demonstrates the intentionally missing
source binding.

A separate external-process baseline publishes real `.malbolge` from canonical
MCTR checkpoints for 1, 7, 64, and 256 pairs using `malbolge_layout
--ternary-file`; every published byte equals the independently reconstructed
direct source. These are real **direct** programs, not guest bytecode artifacts.

## Reproducible pilot

`pilot-v0.toml` records the fixed case family and cost assumptions. No seed is
needed because the bounded generation is deterministic. The size comparison is
only **optimistic**: one byte of candidate data is presumed to require exactly
one Malbolge memory cell, while the actual decoder, loader, envelope, dispatch,
relocation, runtime verification, and error semantics are entirely absent.

The estimated runtime-plus-packaging allowance for a *strictly shorter*
artifact is `direct_code_cells - 7`, if nonnegative. A second sensitivity
scenario reserves 32 **hypothetical** memory cells for source/profile binding,
giving the stricter ceiling `direct_code_cells - 39`. Neither figure includes
an executable interpreter or proves authentic provenance. These are upper
bounds, not observed headroom. See the owning research record for the
complete table, failed small cases, and unresolved acceptance criteria.

## Status

No VM-resident bytecode runtime has been implemented. No guest-interpreted
candidate has been verified, and no compile-time, execution-time, memory,
or verifier-complexity advantage has been measured. The pilot does not satisfy
the P2 adoption criterion.
