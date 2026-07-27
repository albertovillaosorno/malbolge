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
