# Emitted Malbolge static analyzer

## Status

Active implementation

## Purpose

Analyze generated Malbolge for lexical and address validity, self-modification,
control-flow reachability, code/data aliasing, wraparound, dataflow, invalid
executable cells, and input-dependent cycles or hangs.

## Scope

This document governs the following declared TODO scope:

- `verifier/`
- `tests/differential/`
- `tests/exhaustive/`
- `tests/fuzz/`

## Current Behavior

### Implemented initial-image slice

`verifier/emitted_malbolge.py` statically inspects raw `malbolge-1998` source
without executing guest instructions. It applies the historical loader's six
C-locale whitespace bytes, graphical ASCII boundary, two-word recurrence base,
59,049-word capacity, and position-dependent 94-cell decode table. Reports are
canonical JSON and include the exact historical profile identity/capacity,
required source words, SHA-256 of the exact raw source bytes, admitted initial
cells with original byte offsets, stable findings, and analysis limits. Schema
`malbolge-static-image/v12` retains exact `entry_transition` through
`fifth_transition` compatibility fields and adds `bounded_continuations`.
Sixteen transitions remain the default, while one explicit finite request
may select any total bound from 1 through 256. One single-pass finite trace
replays committed writes before each bounded read, then resolves fetch/data
cells,
decode, C/D alias, planned data write, encryption address/input/output,
accumulator dependency, halt/rejection, pointer succession, and wrap. The
prefix transfer canonicalizes effective memory as exact sparse overrides and
can prove repeated concrete `(C,D,A,memory)` state only when the accumulator is
known. Schema v12 does not yet publish that internal cycle certificate.
A `p` whose accumulator depends on prior input is
reported unresolved rather than assigned a guessed value. A non-graphical fetch
is stronger: the preserved 1998 interpreter executes `continue` before decode,
encryption, or pointer advancement, so the unchanged C/D state proves a fixed
fetch cycle. The two-word `b"c'"` fixture reaches exactly that third-step state
at `C=2`, `D=40`, `M[2]=29503`. The three-word `b"('&"` fixture continues
through three exact `j` steps and proves a recurrence-backed fourth fixed-fetch
cycle at `C=3`, `D=39`, `M[3]=29487`. The transfer module now reconstructs
memory/state through one generic next-transition primitive over an explicit
finite accepted prefix. The four-word `b"('&%"` fixture continues through four
`j` steps and then uses that primitive to prove a fifth recurrence-backed fixed
fetch at `C=4`, `D=29490`, `M[4]=29489`. Historical recurrence words are
derived only when a bounded read needs them.
Schema v12 publishes `bounded_fetch_source_map`: each resolved instruction
fetch carries its bounded transition index, fetched address/value, and original
loaded source position/raw byte offset/initial byte when that address belongs to
the loaded source image. Recurrence-only addresses carry null source
coordinates.
The context also distinguishes a still-original source value from an evolved
fetch value without asserting why the value changed. The companion
`bounded_memory_access_source_map` applies the same coordinate rule to every
exact fetch, actual data read, planned data write, and self-encryption address
role in the bounded prefix.
The bounded memory requirement records the sorted addresses touched by
fetch/data/write/encryption semantics and the
minimum word count needed to load the source and reproduce those accesses. A
future pointer value alone is not a memory touch; for example the proven
non-graphical third-step cycle keeps `D=40` without reading address 40.

Initial-image admission is deliberately narrower than whole-program safety.
Schema v12 keeps 16 exact transitions as the default and admits an explicit
finite `transition_limit` from 1 through 256. The CLI exposes the same
request as
`--transition-limit N`. Analysis stops earlier on halt, rejection, fixed-fetch
cycle, or unresolved input-dependent state. The legacy second-through-fifth
fields project the first four continuation records, while memory/source-access
evidence uses the complete selected trace. A 32-cell sequential-output fixture
proves transition 17 and later reporting under an explicit request, and a
256-cell fixture closes the reviewed maximum. The report records the selected
bound in `bounded_transition_limit`, the bounded-memory scope, and every
limit-dependent analysis string. Reachability beyond that selected finite bound,
general dataflow/evolved-memory equivalence, higher-level C/source-map linkage,
complete value-lineage provenance, and longer input-dependent cycle/hang safety
remain open.

## Invariants

- The fixed historical address range is closed structurally; this does not
  imply which addresses are reachable or whether a particular run wraps a
  pointer.
- Per-cell encryption-target classification does not imply reachability. The
  bounded transfer records resolve only the explicitly selected finite prefix.
- Finite-prefix report evidence never implies control flow after the selected
  transition limit. A separate next-transition call requires the caller to
  supply the exact accepted prefix explicitly. Its entry transition is first
  recomputed from the source words, then every continuation record is recomputed
  from the current bounded state before its writes are replayed. General
  reachability remains unproved.
- Every reported initial cell preserves its loaded position and raw-source byte
  offset, and every report binds the exact source bytes and historical profile.
  Bounded fetch and memory-access source context map only addresses in that
  loaded image; recurrence addresses remain explicitly unmapped instead of
  receiving invented offsets.
- Bounded memory evidence counts only addresses actually touched by the analyzed
  prefix and never treats a future code/data pointer as an observed access.
- Future dynamic analyses must state their bounded assumptions rather than
  executing arbitrary guest work to completion or treating unknown as safe.
- The verifier is tested against valid cases and deliberately mutated invalid
  cases so acceptance and rejection boundaries are evidenced independently.

## Failure Behavior

Unknown or unproved equivalence is rejection or an explicitly bounded result,
never implicit acceptance. The CLI prints canonical JSON for both admitted and
rejected initial images, returning a nonzero status when the image is rejected.
Unreadable source fails before a semantic report is emitted.

## Verification

- Expected durable artifact surface: `verifier/`, `tests/differential/`,
  `tests/exhaustive/`, `tests/fuzz/`.
- Required evidence: known-valid fixtures, seeded invalid mutations,
  counterexamples for rejected candidates, and deterministic replay.
- Prerequisite completion evidence: `safe-rust-malbolge-vm`,
  `canonical-malbolge-target-profile`.
- Current executable evidence covers known-valid source, exact loader
  whitespace, lexical rejection, recurrence underflow, historical capacity,
  all 8,836 graphical-byte/position decode pairs against an independent table
  anchored to the preserved historical interpreter `xlat1`, load-admission
  parity anchored to its `strchr("ji*p</vo", ...)` check, historical pointer
  assignment/wrap closure, `i`/`v`/ordinary post-step encryption-target
  classification anchored to the preserved interpreter order, positional decode
  rejection, exact second-step input/no-op/halt/invalid-encryption fixtures,
  explicit input-dependent-crazy unresolved evidence, a 25-case public CLI
  differential including recurrence-backed entry `j`, 16 seeded invalid
  positional mutations with byte-exact replay, exact third/fourth/fifth-step
  halt or fixed-fetch-cycle evidence, recurrence-backed bounded memory
  requirements, default-16 plus explicit-32 and maximum-256 sequential-output
  bound fixtures, bounded loaded-source/raw-offset fetch/read/write/encryption
  provenance,
  byte-exact CLI/library report parity, bounded analysis limits, CLI
  second/third/fourth rejection status, and CLI read failure.

## References

- [Verification Trust Boundary](../adr/verification-trust-boundary.md)

### Governing ADR Paths

- `docs/technical/adr/verification-trust-boundary.md`
