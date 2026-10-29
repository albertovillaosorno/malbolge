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

## Bound follow-up: CEB2 v1 (2026-10-29)

`pilot-v1.toml` and `echo_binding.rs` add a separate, 38-byte research
candidate: four literal `CEB2` bytes, the same little-endian `u16` pair count,
and exactly 32 SHA-256 digest bytes. The digest binds the fixed domain
`CEB2-ternary-profile-v1\0`, the selected *profile fingerprint*, a separator
byte, and the fully validated canonical `malbolge-ternary-ir-v1` wire bytes.
The canonical bytes contain source identifier/hash, guest ABI, profile ID,
function names and every operation/source span. The immutable v0 CEB1 pilot
and its exact six-byte interface remain unchanged.

Both v1 encoding and v1 admission independently revalidate the original
ternary program. Admission rejects an altered digest, unsupported source,
changed count, downgrade to CEB1, truncation or extra bytes. The tests compare
all eight sizes with independently admitted direct layouts, reject every
single-byte mutation of a 38-byte candidate, and reject otherwise-valid
same-count changes to source ID/hash and function name. SHA-256 also passes
published empty, short and multiblock known-answer vectors. This is
**byte equality binding**, not source authentication: a malicious publisher
could still supply matching forged source and candidate, and the caller must
trust the original canonical ternary program and profile.

At the same intentionally optimistic one-byte-per-memory-cell assumption, v1
requires `R + 38 < 2n + 1` for a strict code-size win. The maximum allowable
missing guest-runtime cells at `n=1,7,20,256,2047` are respectively
`None, None, 2, 474, 4056`. The v0 hypothetical +32-cell column shares those
numerical thresholds, but v1 actually carries 32 digest *bytes* in its
research descriptor; it still does **not** prove 32 Malbolge data cells can
hold those bytes or account for a guest digest/decoder, loader, provenance
anchor, source availability, or any real interpreter. It also does not reduce
execution time. The CEB2 envelope is expanded **on the host** to the exact
same executable **direct** source, never interpreted by a guest bytecode VM.

## Status

No VM-resident bytecode runtime has been implemented. No guest-interpreted
candidate has been verified, and no compile-time, execution-time, memory,
or verifier-complexity advantage has been measured. The pilot does not satisfy
the P2 adoption criterion.
