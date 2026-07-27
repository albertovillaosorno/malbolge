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
