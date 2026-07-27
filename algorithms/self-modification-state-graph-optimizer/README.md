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
