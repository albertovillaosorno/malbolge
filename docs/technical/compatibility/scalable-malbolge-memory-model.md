# Scalable Malbolge memory model

## Status

Accepted implementation

## Purpose

Remove the historical 59,049-word ceiling from current Malbolge without
creating a separately branded extended language. Scaling remains ternary: an
`N`-trit profile has one `N`-trit word domain and exactly `3^N` directly
addressable words. The frozen `malbolge-1998` profile remains exactly ten trits
and 59,049 words.

## Scope

This document governs the following declared TODO scope:

- `malbolge.json`
- `compatibility/`
- `docs/technical/specification/`
- `tests/compatibility/`
- `src/runtime/virtual-machine/domain/profile_machine.rs`
- `src/runtime/virtual-machine/composition/build.rs`
- `tests/vm/profile_machine.rs`

## Current Behavior

### Profile Model

For a target profile with `N` trits, define `W_N = 3^N`.

- A machine word is an unsigned value in `0..=W_N-1`.
- Memory contains exactly `W_N` words.
- `A`, `C`, `D`, memory words, and direct addresses use that same word domain.
- `C` and `D` advance modulo `W_N`.
- No host pointer width, virtual-memory page size, decimal multiplier, or
  implementation-language integer width participates in guest addressing.

Schema version 2 deliberately selects this single-word ternary geometry instead
of a paged or multiword address scheme. A later schema may add another model,
but it must use a new explicit profile identity.

### Ternary Operations

The defining operations generalize with the profile width rather than acquiring
new truth tables.

Rotation of `x` is the same one-trit circular right rotation used by the 1998
machine:

`rotate_N(x) = floor(x / 3) + (x mod 3) * 3^(N-1)`.

The crazy operation applies the original 3-by-3 crazy truth table independently
to exactly `N` corresponding trit pairs. Increasing `N` adds trit positions; it
does not change the operation on any existing position.

The loader recurrence remains the same recurrence over profile-width words.
Positional decode retains the historical 94-entry translation rule: the
profile-width numeric `C` participates in the same modulo-94 decode phase.
Post-instruction encryption remains the historical graphical-cell translation.
Self-modification therefore remains fundamental rather than being weakened to
make larger memory easier to implement.

### Input, Output, and EOF

`/` remains byte input and `<` remains output. Output is still `A mod 256`.

EOF is the maximum profile word, preserving the historical all-two-trit
sentinel:

`EOF_N = 3^N - 1`.

For `malbolge-1998`, this is 59,048. For the current N15 reference geometry it
is 14,348,906.

### Versioned Profiles

The canonical identities are currently:

- `malbolge-1998`: historical conformance, `N = 10`, 59,049 words.
- `malbolge-2026.1`: retained versioned transition identity, `N = 10`.
- `malbolge-2026.2`: immutable first scalable profile, `N = 14`, 4,782,969
  words.
- `malbolge-2026.3`: immutable interpreter-compatible transition profile,
  `N = 14`, 4,782,969 words.
- `malbolge-2026`: official current reference, `N = 15`, 14,348,907 words with
  interpreter-compatible I/O assignment.

Published versioned profiles are immutable. The annual `malbolge-2026` current
reference may advance repository fallback geometry, but its fingerprint changes
with that geometry, so an artifact bound to an older fingerprint never silently
acquires new semantics. The semantic-width model itself has no mathematical
maximum; N15 is a concrete current reference and backend envelope, not a
language ceiling.

### Why Versioned Profiles Retain Fourteen Trits

The tracked normalized DOOM development oracle currently contains 2,479,932
source bytes. This is only a lower-bound workload proxy: source bytes are not a
prediction of compiled Malbolge words. The evidence artifact also retains the
1,497,009-byte snapshot used when `malbolge-2026.2` was originally selected.

Thirteen trits provide 1,594,323 words and are now 885,609 words below the
tracked source proxy. Fourteen trits provide 4,782,969 words and remain the
first native ternary width above that proxy, with 2,303,037 words of headroom.
That evidence still justifies the immutable `malbolge-2026.2` and
`malbolge-2026.3` geometries; it is not a maximum-width argument.

The current reference is N15 so the fallback exercises three complete five-trit
chunks. This is not a claim that DOOM now fits after compilation, nor evidence
that N15 is universally optimal. Future compiler/runtime measurements and
verified per-program width evidence remain authoritative.

The exact source snapshot and candidate arithmetic are retained in
<!-- jig-ignore-next-line: canonical path or identifier is indivisible -->
`src/interoperability/profile-compatibility/contract/scalable-memory-evidence.json`.

### Implementation Status

`malbolge.json` schema version 2 defines the immutable scalable identities and
selects `malbolge-2026`.
`tests/compatibility/test_scalable_memory.py` independently verifies profile
geometry, N-trit rotate, digitwise crazy, EOF, wraparound, and the link to the
tracked DOOM evidence snapshot.

Safe Rust now has an explicit profile-driven interpreter in
`src/runtime/virtual-machine/domain/profile_machine.rs`. `ProfileMachine` owns
`u32` profile-width registers
and an exact `profile.memory_words()` image, preflights against runtime identity
`safe-rust-profiled`, and executes the same normative sequential decode, crazy,
rotate, byte I/O, self-modification, post-instruction encryption, and pointer
wrap rules. The current canonical reference is N15/14,348,907 words. The
profiled `u32` representation envelope is independently N20/3,486,784,401 words;
physical allocation remains a separate resource-planning concern.

The five-trit crazy lookup table is generated once as profile-neutral ternary
math and shared by both classic and profile-driven engines. Current N15 is three
complete chunks. Immutable N14 profiles use 5+5+4, with only the final partial
chunk zero-padded before projection.


The public `ChunkedProfileWord` contract now represents those chunks directly.
Its chunk width/cardinality come from the generated Rust projection of the
canonical semantic-width model, whose maximum remains `None`. Crazy and rotate
operate across any allocated number of chunks; the final incomplete chunk keeps
only its semantic trits exactly as the canonical padding/projection rule
requires. The same value contract now provides modular successor and small
residue without constructing `3^N`, which are the value operations needed by
wide C/D pointer movement and instruction/output projection.

This is value-level scalability, not yet a scalable memory image.
`ProfileMachine`
and resident/native execution still use `u32` words and addresses through N20;
the chunked contract provides the non-fixed-width value primitive needed for a
later memory/pointer migration without moving the semantic ceiling to `u64`.

`Machine` and `ExecutionMachine` intentionally remain the frozen/classic
surface.
They still reject `malbolge-2026` through `safe-rust-classic` preflight rather
than silently changing classic types or loader behavior. `ProfileMachine` is the
explicit runtime surface for current scalable execution. Native tiers, CUDA
resident execution, decompiler output, runtime capability checks, and benchmark
workloads consume canonical profile geometry. Future compiler and integrated

verifier implementations own their adoption before becoming executable.

## Invariants

- `malbolge-1998` remains exactly ten trits and 59,049 words.
- Every schema-v2 profile uses radix 3 and `word.modulus = 3^trits`.
- `single-word-modular` memory has exactly `word.modulus` words.
- EOF is exactly `word.modulus - 1`.
- Scaling does not change sequential deterministic guest execution, crazy,
  rotate, self-modification, post-encryption, or byte-I/O meanings.
- Exactly one profile has `kind = "current"`, and it is named by
  `current_profile`.
- Published versioned profile identities remain immutable. Advancing the annual
  current reference changes its fingerprint and never mutates versioned `.2/.3`
  geometry or previously fingerprint-bound artifacts.
- `Machine` remains exact classic conformance; scalable execution is selected
  explicitly through `ProfileMachine` rather than changing classic word types.

## Failure Behavior

A consumer that cannot implement the selected profile fails explicitly before
execution or compilation. It never truncates an address, clamps a word, silently
falls back to 59,049 words, or borrows host pointer behavior.

## Verification

- `python
  src/automation/repository/composition/scripts/validate/target_profile.py`
  validates the closed profile
  schema and cross-profile invariants.
- `tests/test_target_profile.py` covers schema/profile failure boundaries.
- `tests/compatibility/test_scalable_memory.py` independently checks scalable
  ternary geometry and the workload-evidence link.
<!-- jig-ignore-next-line: canonical path or identifier is indivisible -->
- `src/interoperability/profile-compatibility/contract/scalable-memory-evidence.json`
  retains the exact tracked source
  hash, source-byte proxy, candidate capacities, and selected profile.
- `tests/vm/profile_machine.rs` executes the full 4,782,969-word current
  profile,
  verifies addresses above 59,048, and checks 14-trit crazy/rotate effects
  against
  independent scalar formulas.
- The same Rust suite executes `ProfileMachine` under `malbolge-1998` and
  compares
  all 59,049 final memory words, registers, I/O, EOF behavior, and termination
  against the classic `Machine`.
- `tests/vm/profile_tracing.rs` locks current-profile trace identity, current
  EOF,
  trace inertness, and atomic rejection from a real 14-trit recurrence target.

## References

- [Specification Authority And Malbolge
  Evolution](../adr/specification-authority-and-malbolge-evolution.md)
- [Canonical Malbolge target profile](../specification/target-profile.md)

### Governing ADR Paths

- `docs/technical/adr/specification-authority-and-malbolge-evolution.md`
