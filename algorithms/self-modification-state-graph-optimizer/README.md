# Self-modification state-graph optimizer

This directory is the executable mirror for research ID
`self-modification-state-graph-optimizer`. The human research record uses the
same ID under `docs/research/algorithms/`, and its mathematical contract, when
present, uses the same ID under `math/algorithms/`.

Implementations in Rust, C, CUDA, Python, or another justified language live
together here because the algorithm, not the language, owns the research.
Regenerable results belong in `out/` and remain Git ignored.

The active first slice is `state_graph.rs`: a classic-profile exact-state graph
that uses deterministic hashing only as a bucket index and confirms every merge
against complete input/output/register/termination/memory snapshots. The
collision fixture deliberately maps all states to one digest to prove hashing is
not a correctness authority. Reduced-state keys remain research candidates only.

The first admitted reduction is `future_input_snapshot`: it keeps the committed
input cursor and exact remaining suffix but drops the contents of bytes strictly
before the cursor. `exact.rs` exhausts all 256 possible consumed first bytes in a
converging two-input fixture before accepting this reduction.

The second admitted reduction is `terminal_future_snapshot`. For an already
terminated classic machine it retains only profile identity, committed output,
and termination reason; memory/register/input state is dead for future requests.
The projection rejects live machines fail-closed.

`profile.rs` extends the exact baseline to validated `ProfileMachineState`
checkpoints, including the current 14-trit/4,782,969-word profile. It consumes the
runtime checkpoint directly, hashes only for bucket selection, and confirms every
merge with full checkpoint equality. This is a correctness/deoptimization oracle,
not a claim that full-checkpoint graph storage is economical.

The exact current-checkpoint cost is measured by `bench.rs`. Versioned evidence
under `benchmarks/research/state-graph/evidence/2026-07-27-windows-x86_64/`
records 15 samples per operation. The current host median is 7.19 ms to clone a
checkpoint, 26.24 ms to digest/insert a prepared checkpoint, and 30.76 ms to
digest/confirm an exact replay. These values reject full-checkpoint copying and
hashing as the default per-step production graph representation on this host.

`tests/d.rs` establishes the profile-size-independent memory mutation bound:
every requested normative step changes at most two memory cells. It compares
complete before/after memories for all instruction families in classic and
current profiles, including real two-cell crazy/rotate cases and zero-cell
halt/rejection. This is the prerequisite for a persistent/delta memory graph.

The VM trace now exposes the proved memory delta directly. Classic `MemoryDelta`
and current `ProfileMemoryDelta` contain at most the distinct data/encryption
changes committed by the real step engine. `tests/d.rs` independently scans full
before/after memory and requires exact address/before/after equality, so future
persistent nodes can consume the trace without making it a correctness oracle.

`memory.rs` is the first concrete alternative to per-step full checkpoints.
It stores one `Arc<[u32]>` root plus immutable `ProfileMemoryDelta` patch nodes.
Every patch validates its trace `before` values against the current persistent
view, empty deltas reuse depth, reads search newest patches before the root, and
`materialize()` exists as an oracle. Current traced execution reconstructs every
full runtime checkpoint exactly in `tests/p.rs`.

The linked patch chain is now rejected as a general lookup structure. Post-commit
depth measurements keep newest-patch hits near 18 ns, but root misses grow to
20751.17 ns at depth 4096. Periodic full compaction also retains a
multi-microsecond modeled lower bound on the measured host. The next memory
candidate must keep structural sharing while bounding arbitrary read depth.

`index.rs` is the bounded-read candidate selected after the linked-chain depth
experiment. It keeps the same shared full root but stores overrides in a
persistent 64-way radix over four six-bit address chunks. Current 14-trit
addresses fit within the explicit 24-bit research capacity. Reads therefore
inspect at most four radix levels before either finding an override or falling
back to the root; writes validate trace `before` values and path-copy only the
affected radix nodes. `tests/i.rs` reconstructs real current checkpoints and
exercises 4096 distinct overrides.

Post-commit evidence at `ec459d0` promotes the radix as the current-profile
memory candidate. Through 4096 distinct overrides, indexed latest/root reads stay
near 20--25 ns while indexed apply stays around 0.9--1.2 microseconds for one new
override. At depth 4096 the linked root miss is
24.12 microseconds versus
20.70 ns for the radix (~1165x ratio).
The remaining blocker is exact indexed-memory identity/dedup without full
materialization.

`state.rs` closes the per-observation full-checkpoint identity bottleneck for one
execution lineage. It stores immutable input/root lineage by shared `Arc`, evolves
all changing fields from public `ProfileStepTrace`, keeps output and radix
digests incrementally, and uses the resulting constant-size digest only for
bucket selection. Exact output/scalar/radix equality still confirms every merge.
Foreign roots fail closed instead of triggering a complete memory comparison.
`tests/s.rs` reconstructs every current checkpoint exactly, forces digest
collisions, and verifies exact replay deduplication.

Post-commit identity evidence at `f317f3e` promotes the lineage-bound incremental
graph. New-state observation measures 535.82
ns/op and exact replay 406.67 ns/op, versus
26.29 ms and
30.48 ms for complete-checkpoint insert/replay. The
measured representation ratios are about
49070x and
74958x respectively. The remaining
history-sized field is committed output, currently cloned as `Vec<u8>` on append.

`output.rs` removes the remaining per-step clone of complete committed output
without changing observable identity. It stores the checkpoint output prefix in
one shared `Arc<[u8]>` and appends immutable one-byte tail nodes. Exact equality
retains byte authority after digest/length filters, materialization reconstructs
the complete output, and iterative destruction prevents recursive-`Arc` stack
overflow on long unique histories. `state.rs` now uses this persistent history in
its exact merge key and oracle checkpoints.

Post-commit output evidence at `1d229d0` promotes persistent output storage. The
append candidate stays about 108--145 ns/op from empty through 256 KiB histories;
the prior complete-`Vec` clone rises from about 84 ns to 20.83 microseconds. At
256 KiB the measured representation ratio is about 144x. The small empty-history
penalty is accepted because persistent append removes history-length scaling from
ordinary state updates. Native-region safety/guards are now the next state-graph
research boundary.

`region.rs` introduces the first verifier-admitted native-shortcut class without
emitting native code yet. `ExactRegionCertificate` is explicitly untrusted; its
entry, bounded outcome, full normative trace sequence, and exact exit are
re-executed by `verify()`. Only the resulting `VerifiedExactRegion` may be reused,
and only when `accepts_entry()` confirms exact incremental-state equality. Digest
identity is never a guard. Mutated entries deopt/reject, tampered claims fail
reverification, and normative transition errors never produce verified regions.
This is deliberately an exact-state specialization baseline; broader dependency
guards remain research.

Post-commit region evidence at `f16785d` measures exact guard hit/miss at
55.51/59.09 ns/op and full normative
certificate verification at 9.09 ms. This is the
intended trust split: expensive cold verification, cheap hot exact guards. Future
read-set guards are therefore motivated by safe reuse across memory variants,
not by a need to reduce the ~55 ns exact guard itself.

The normative `ProfileStepTrace` now supplies the missing dependency authority:
`memory_reads` records at most three real semantic roles (fetch, optional data,
optional encryption) directly from the transition engine. The VM fixture table
covers every instruction family and preserves reads completed before rejected
jump encryption. Region live-in analysis can therefore be derived from observed
read-before-write behavior instead of re-decoding opcodes in research code.

Verified regions now derive a reduced memory guard by ordered read-before-write
analysis over the VM-provided semantic read set and exact memory delta. A cell is
a live-in dependency only when the region reads it before any earlier verified
region write dominates that address. The guard still requires exact non-memory
state and the same immutable lineage. After it passes, verified after-values are
applied to the candidate while memory outside the verified write set is
preserved. `tests/r.rs` proves an irrelevant-memory variant fails the exact guard
but safely reuses the region and matches direct VM execution exactly; changing a
live-in dependency fails closed.

`artifact.rs` is the portable effect-IR trust-boundary precursor. An untrusted
claim carries only schema version, profile fingerprint, verifier-derived live-ins,
step budget, outcome, and compact state-changing effects. Admission independently
reprojects every effect from `VerifiedExactRegion` traces and compares every
field exactly. Only the verified artifact type may execute; guard miss retains the
same normative deoptimization path. This is not yet architecture machine code or
a stable cross-process cache format.
